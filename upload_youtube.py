import requests
import os
from supabase import create_client
from dotenv import load_dotenv


load_dotenv()


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user_level(user_id):
    response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
    
    if response.data:
        return response.data["level"]
    else:
        return None  # Если уровень не найден, возвращаем None


def fetch_youtube_videos(user_level):
    query = f"English listening practice {user_level}"  # Формируем запрос

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&videoDuration=short&maxResults=10&key={YOUTUBE_API_KEY}"
    
    response = requests.get(url)
    data = response.json()

    videos = []
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        videos.append({
            "title": title,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "level": user_level,
            "required_words": 50
        })
    
    return videos


def save_videos_to_supabase(videos):
    for video in videos:
        supabase.table("listening_content").upsert(video).execute()


if __name__ == "__main__":
    user_id = "ID_ПОЛЬЗОВАТЕЛЯ"  # Укажи ID пользователя, для которого ищем видео
    user_level = get_user_level(user_id)

    if user_level:
        print(f"🔹 Уровень пользователя: {user_level}")
        videos = fetch_youtube_videos(user_level)
        save_videos_to_supabase(videos)
        print("Видео успешно загружены в Supabase!")
    else:
        print("Ошибка: уровень пользователя не найден в базе.")
