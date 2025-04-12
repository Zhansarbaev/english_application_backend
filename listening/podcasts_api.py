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

async def fetch_podcasts(user_level, topic=None):
    """Асинхронно получает подкасты из ListenNotes API по уровню пользователя и фильтрует по уровню в названии."""
    query = f"English {user_level}"
    if topic:
        query += f" {topic}"
    
    url = f"https://listen-api.listennotes.com/api/v2/search?q={query}&type=episode&language=English"
    headers = {"X-ListenAPI-Key": LISTEN_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail=f"Ошибка ListenNotes API: {await response.text()}")
                
                data = await response.json()
                podcasts = []
                for item in data.get("results", []):
                    try:
                        title = html.unescape(item.get("title_original", ""))
                        description = html.unescape(item.get("description_original", ""))

                        language = detect(description) if description.strip() else "en"
                        if language != "en":
                            continue
                        
                        # Фильтрация подкастов по уровню, указанному в заголовке
                        if user_level.lower() not in title.lower():
                            continue
                    except Exception:
                        continue
                    
                    if "audio" in item and item["audio"]:
                        podcasts.append({
                            "title": title,
                            "audio_url": item["audio"],
                            "image": item["image"],
                            "level": user_level
                        })
                return podcasts[:3]
    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к ListenNotes API: {str(e)}")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Время ожидания запроса к ListenNotes API истекло. Попробуйте позже.")

async def transcribe_audio(audio_url: str) -> str:
    """Асинхронно расшифровывает аудио через Deepgram без ограничения по времени."""
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    params = {"model": "general", "tier": "base", "language": "en"}

    print(f"Начинаем скачивание аудиофайла: {audio_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as audio_resp:
                if audio_resp.status != 200:
                    print(f"Ошибка загрузки аудиофайла: {await audio_resp.text()}")
                    return ""
                
                print(f"Аудиофайл загружен, отправка в Deepgram...")
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
    """Проверяет, есть ли уже транскрипции по теме и пользователю (игнорируя регистр), если нет — транскрибирует и сохраняет."""
    print(f"Проверка транскрипции для user_id={user_id}, topic={topic}")
    
    existing_transcripts = supabase.from_("user_transcripts").select("topic").eq("user_id", user_id).execute()
    
    existing_topics = {t["topic"].lower() for t in existing_transcripts.data}
    
    if topic.lower() in existing_topics:
        print(f"Транскрипция уже существует для user_id={user_id}, topic={topic}. Пропускаем обработку.")
        return
    
    print(f"🎙 Начало транскрипции подкастов: {len(podcasts)} шт.")
    
    for podcast in podcasts:
        transcript = await transcribe_audio(podcast["audio_url"])
        if transcript.strip():
            print(f"Сохранение транскрипции подкаста: {podcast['title']}")
            supabase.from_("user_transcripts").insert({
                "id": str(uuid4()),
                "user_id": user_id,
                "podcast_title": podcast["title"],
                "transcript": transcript,
                "topic": topic,
                "created_at": "now()"
            }).execute()
        else:
            print(f"Ошибка: транскрипция пустая для {podcast['title']} или произошла ошибка")

@router.get("/podcasts")
async def get_podcasts(user_id: str, topic: str = Query(None)):
    """Получает подкасты по выбранной теме и уровню пользователя, затем проверяет необходимость транскрипции."""
    try:
        response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        user_level = response.data["level"]
        podcasts = await fetch_podcasts(user_level, topic)
        
        if not podcasts:
            return {"message": "Подкасты не найдены.", "podcasts": []}
        
        print(f"Запуск транскрипции в фоне для user_id={user_id}, topic={topic}")
        asyncio.create_task(process_podcasts(user_id, topic, podcasts))
        
        return {"podcasts": podcasts, "transcription_status": "Транскрипция запущена!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
