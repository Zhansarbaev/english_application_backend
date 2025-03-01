import os
import requests
import aiohttp
from uuid import UUID
from langdetect import detect
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Depends

# Загружаем переменные окружения
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LISTEN_API_KEY = os.getenv("LISTEN_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создаем FastAPI Router
router = APIRouter()

def fetch_podcasts(user_level: str, topic: str = None):
    """Получает подкасты из ListenNotes API по уровню пользователя."""
    query = f"English {user_level}"
    if topic:
        query += f" {topic}"
    
    url = f"https://listen-api.listennotes.com/api/v2/search?q={query}&type=episode&language=English"
    headers = {"X-ListenAPI-Key": LISTEN_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    data = response.json()
    podcasts = []
    
    for item in data.get("results", []):
        try:
            description = item.get("description_original", "")
            language = detect(description) if description.strip() != "" else "en"
            if language != "en":
                continue
        except Exception:
            continue
        
        if "audio" in item and item["audio"]:
            podcasts.append({
                "title": item["title_original"],
                "audio_url": item["audio"],
                "image": item["image"],
                "level": user_level
            })
    
    return podcasts[:3]

async def transcribe_audio(audio_url: str) -> str:
    """Отправляет аудиофайл в Deepgram и получает расшифровку."""
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    params = {"model": "general", "tier": "base", "language": "en"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.deepgram.com/v1/listen", headers=headers, params=params, data=requests.get(audio_url).content) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=500, detail="Ошибка Deepgram API")
            result = await resp.json()
    
    return result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

@router.get("/transcribe_podcast")
async def transcribe_podcast(user_id: UUID = Query(...), topic: str = Query(None)):
    """Получает подкасты для пользователя и делает транскрипцию через Deepgram."""
    try:
        response = supabase.from_("users_progress").select("level").eq("user_id", str(user_id)).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        user_level = response.data["level"]

        podcasts = fetch_podcasts(user_level, topic)
        if not podcasts:
            return {"message": "Подкасты не найдены."}

        transcripts = {}
        for podcast in podcasts:
            text = await transcribe_audio(podcast["audio_url"])
            transcripts[podcast["title"]] = text

        return {"transcripts": transcripts}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
