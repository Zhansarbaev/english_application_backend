import os
import requests
from langdetect import detect
from supabase import create_client
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query

# Загружаем переменные окружения
load_dotenv()
LISTEN_API_KEY = os.getenv("LISTEN_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создаем FastAPI Router
router = APIRouter()

def fetch_podcasts(user_level, topic=None):
    # Формируем запрос: основной текст "English" + уровень и тема (если есть)
    query = f"English {user_level}"
    if topic:
        query += f" {topic}"
    
    # Указываем параметр language=English, чтобы попытаться получать только английские подкасты
    url = f"https://listen-api.listennotes.com/api/v2/search?q={query}&type=episode&language=English"
    headers = {"X-ListenAPI-Key": LISTEN_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Ошибка API ListenNotes: {response.status_code} - {response.text}")
        return []
    
    data = response.json()
    podcasts = []
    
    for item in data.get("results", []):
        # Дополнительная проверка языка с использованием langdetect
        try:
            description = item.get("description_original", "")
            # Если нет описания, предполагаем английский (или можно пропускать)
            language = detect(description) if description.strip() != "" else "en"
            if language != "en":
                continue  # Пропускаем подкаст, если язык не английский
        except Exception as e:
            # Если определить язык не удалось, пропускаем этот элемент
            continue
        
        if "audio" in item and item["audio"]:
            podcasts.append({
                "title": item["title_original"],
                "audio_url": item["audio"],
                "image": item["image"],
                "level": user_level
            })
    
    # Ограничиваем вывод до 3 подкастов
    return podcasts[:3]

@router.get("/podcasts")
async def get_podcasts(user_id: str, topic: str = Query(None)):
    try:
        response = supabase.from_("users_progress").select("level").eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="❌ Пользователь не найден")
        user_level = response.data["level"]
        podcasts = fetch_podcasts(user_level, topic)
        if not podcasts:
            return {"message": "❗ Подкасты не найдены. Попробуйте изменить тему.", "podcasts": []}
        return {"podcasts": podcasts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Ошибка сервера: {str(e)}")
