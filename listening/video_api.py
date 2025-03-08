import os
import aiohttp
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

async def fetch_youtube_videos(user_level, topic=None):
    """Асинхронно получает видео с YouTube API."""
    query = f"English listening {user_level}"
    if topic:
        query += f" {topic}"

    url = (
        f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&"
        f"type=video&videoDuration=short&maxResults=5&key={YOUTUBE_API_KEY}"
    )
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=500, detail=f"Ошибка YouTube API: {await response.text()}")
            
            data = await response.json()
            videos = []
            for item in data.get("items", []):
                video_id = item["id"].get("videoId")
                title = item["snippet"].get("title", "Без названия")
                if video_id:
                    videos.append({
                        "title": title,
                        "video_url": f"https://www.youtube.com/watch?v={video_id}",
                        "level": user_level
                    })
            return videos

@router.get("/videos")
async def get_videos(user_id: str, topic: str = Query(None)):
    """Получает обучающие видео на основе уровня пользователя."""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        user_level = response.data["level"]
        videos = await fetch_youtube_videos(user_level, topic)
        
        if not videos:
            return {"message": "Видео не найдены. Попробуйте изменить тему.", "videos": []}
        
        return {"videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")