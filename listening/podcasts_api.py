import os
import asyncio
import aiohttp
from uuid import uuid4
from langdetect import detect
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
import html

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LISTEN_API_KEY = os.getenv("LISTEN_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
router = APIRouter()

MAX_DURATION_SEC = 15 * 60  # 15 минут

# 🔍 Асинхронная проверка одного подкаста
async def validate_podcast(item, session, user_level, seen_titles):
    try:
        title = html.unescape(item.get("title_original", "")).strip()
        description = html.unescape(item.get("description_original", "")).strip()
        duration = item.get("audio_length_sec", 0)
        audio_url = item.get("audio", "").strip()

        if title in seen_titles:
            print(f"⏩ Дубликат: {title}", flush=True)
            return None
        seen_titles.add(title)

        if duration > MAX_DURATION_SEC:
            print(f"⏩ Пропущен (длина > 15 мин): {title}", flush=True)
            return None

        language = detect(description) if description else "en"
        if language != "en":
            print(f"⏩ Пропущен (не en): {title}", flush=True)
            return None

        must_have_keywords = ["learn", "study", "practice", "lesson", "english"]
        if not any(word in description.lower() for word in must_have_keywords):
            print(f"⏩ Пропущен (нет ключевых слов): {title}", flush=True)
            return None

        blacklist = [
            "italian", "german", "french", "spanish", "portuguese", "russian", "chinese", "japanese",
            "travel blog", "holiday planner", "tourism podcast"
        ]
        if any(bad in title.lower() or bad in description.lower() for bad in blacklist):
            print(f"⏩ Пропущен (blacklist): {title}", flush=True)
            return None

        if not audio_url:
            print(f"⛔️ Пропущен (нет audio_url): {title}", flush=True)
            return None

        # Проверка аудиофайла
        audio_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*",
            "Range": "bytes=0-1"
        }

        async with session.get(audio_url, headers=audio_headers, allow_redirects=True) as audio_resp:
            if audio_resp.status >= 400:
                print(f"❌ Аудиофайл недоступен ({audio_resp.status}): {audio_url}", flush=True)
                return None

            content_type = audio_resp.headers.get("Content-Type", "")
            if not content_type.startswith("audio"):
                print(f"⛔️ Пропущен (не audio Content-Type): {audio_url} — {content_type}", flush=True)
                return None

        return {
            "title": title,
            "audio_url": audio_url,
            "image": item.get("image"),
            "level": user_level,
            "duration": duration
        }

    except Exception as e:
        print(f"⚠️ Ошибка при обработке подкаста: {e}", flush=True)
        return None

# 🚀 Основная функция
async def fetch_podcasts(user_level, topic=None):
    query = f"Learn English {topic}" if topic else "Learn English"
    url = "https://listen-api.listennotes.com/api/v2/search"
    headers = {"X-ListenAPI-Key": LISTEN_API_KEY}
    params = {
        "q": query,
        "type": "episode",
        "language": "English",
        "len_max": 15,
        "sort_by_date": 0,
        "offset": 0,
        "only_in": "title,description",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail=f"Ошибка ListenNotes API: {await response.text()}")

                data = await response.json()
                seen_titles = set()

                # Параллельно валидируем все эпизоды
                tasks = [
                    validate_podcast(item, session, user_level, seen_titles)
                    for item in data.get("results", [])
                ]
                results = await asyncio.gather(*tasks)
                podcasts = [p for p in results if p is not None]

                print(f"🔎 Найдено {len(podcasts)} подходящих подкастов", flush=True)
                return podcasts[:3]

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к ListenNotes API: {str(e)}")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Время ожидания запроса истекло.")






async def transcribe_audio(audio_url: str) -> str:
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    params = {"model": "general", "tier": "base", "language": "en"}

    print(f"Начинаем скачивание аудиофайла: {audio_url}", flush=True)


    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }) as audio_resp:

                if audio_resp.status != 200:
                    print(f"Ошибка загрузки аудиофайла: {await audio_resp.text()}", flush=True)
                    return ""

                print(f"Аудиофайл загружен, отправка в Deepgram...", flush=True)
                content_type = audio_resp.headers.get("Content-Type", "")
                if not content_type.startswith("audio"):
                    print(f"⚠️ Не аудиофайл! Получен Content-Type: {content_type}")
                    return ""

                audio_data = await audio_resp.read()

                async with session.post("https://api.deepgram.com/v1/listen", headers=headers, params=params, data=audio_data) as resp:
                    if resp.status != 200:
                        print(f"Ошибка Deepgram API: {await resp.text()}")
                        return ""

                    result = await resp.json()
    except aiohttp.ClientError as e:
        print(f"Ошибка сети при транскрипции: {str(e)}")
        return ""

    print(f"Транскрипция получена!")
    return result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

async def process_podcasts(user_id: str, topic: str, podcasts: list):
    print(f"Проверка транскрипции для user_id={user_id}, topic={topic}", flush=True)

    existing_transcripts = supabase.from_("user_transcripts").select("topic").eq("user_id", user_id).execute()
    existing_topics = {t["topic"].lower() for t in existing_transcripts.data}

    if topic.lower() in existing_topics:
        print(f"Транскрипция уже существует для user_id={user_id}, topic={topic}. Пропускаем обработку.", flush=True)
        return

    print(f"🎙 Начало транскрипции подкастов: {len(podcasts)} шт.", flush=True)

    for podcast in podcasts:
        transcript = await transcribe_audio(podcast["audio_url"])
        if transcript.strip():
            print(f"Сохранение транскрипции подкаста: {podcast['title']}", flush=True)
            supabase.from_("user_transcripts").insert({
                "id": str(uuid4()),
                "user_id": user_id,
                "podcast_title": podcast["title"],
                "transcript": transcript,
                "topic": topic,
                "created_at": "now()"
            }).execute()
        else:
            print(f"Ошибка: транскрипция пустая для {podcast['title']} или произошла ошибка", flush=True)

@router.get("/podcasts")
async def get_podcasts(user_id: str, topic: str = Query(None)):
    try:
        response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        user_level = response.data["level"]
        podcasts = await fetch_podcasts(user_level, topic)

        if not podcasts:
            return {"message": "Подкасты не найдены.", "podcasts": []}

        print(f"Запуск транскрипции в фоне для user_id={user_id}, topic={topic}", flush=True)
        asyncio.create_task(process_podcasts(user_id, topic, podcasts))

        return {"podcasts": podcasts, "transcription_status": "Транскрипция запущена!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
