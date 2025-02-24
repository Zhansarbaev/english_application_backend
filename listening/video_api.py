import os
import requests
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, Query

# 🔹 Загружаем переменные из .env
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 🔹 Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 Создаём роутер
router = APIRouter()

# 🔹 Функция поиска видео
def fetch_youtube_videos(user_level, topic=None):
    query = f"English listening {user_level}"
    if topic:
        query += f" {topic}"

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&videoDuration=short&maxResults=5&key={YOUTUBE_API_KEY}"
    
    response = requests.get(url)
    data = response.json()

    videos = []
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        videos.append({
            "title": title,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "level": user_level
        })
    
    return videos

# 🔹 API для получения видео
@router.get("/videos")
async def get_videos(user_id: str, topic: str = Query(None)):
    response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
    
    if not response.data:
        return {"error": "Пользователь не найден"}

    user_level = response.data["level"]
    videos = fetch_youtube_videos(user_level, topic)

    return {"videos": videos}
