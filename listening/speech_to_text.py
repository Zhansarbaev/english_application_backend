import os
import asyncio
import aiohttp
from uuid import uuid4
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException


load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

async def transcribe_audio(audio_url: str) -> str:
    """Асинхронно расшифровывает аудио через Deepgram."""
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    params = {"model": "general", "tier": "base", "language": "en"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(audio_url) as audio_resp:
            if audio_resp.status != 200:
                raise HTTPException(status_code=500, detail=f"Ошибка загрузки аудиофайла: {await audio_resp.text()}")
            
            audio_data = await audio_resp.read()
            async with session.post("https://api.deepgram.com/v1/listen", headers=headers, params=params, data=audio_data) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail=f"Ошибка Deepgram API: {await resp.text()}")
                
                result = await resp.json()
    
    return result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

async def process_podcasts(user_id: str, podcasts: list, topic: str):
    """Обрабатывает список подкастов: транскрибирует и сохраняет в Supabase."""
    tasks = [transcribe_audio(podcast["audio_url"]) for podcast in podcasts]
    transcripts = await asyncio.gather(*tasks)
    
    for podcast, transcript in zip(podcasts, transcripts):
        supabase.from_("user_transcripts").insert({
            "id": str(uuid4()),
            "user_id": user_id,
            "podcast_title": podcast["title"],
            "transcript": transcript,
            "topic": topic,  
            "created_at": "now()"
        }).execute()
    
    return {"message": "Транскрипции сохранены!"}

@router.post("/transcribe_podcasts")
async def transcribe_podcasts(user_id: str, topic: str, podcasts: list):
    """Запускает транскрипцию подкастов и сохраняет в Supabase."""
    try:
        return await process_podcasts(user_id, podcasts, topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка транскрипции: {str(e)}")
