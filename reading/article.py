import os
import json
import random
import openai
from supabase import create_client
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

router = APIRouter()

# Pydantic-модели
class TopicRequest(BaseModel):
    user_id: str

class GenerateArticleRequest(BaseModel):
    user_id: str
    topic: str

class MarkAsReadRequest(BaseModel):
    user_id: str
    topic: str

class HistoryRequest(BaseModel):
    user_id: str

#  Логирование
def log_message(label, data):
    print(f"{label}: {json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, dict) else data}")

# Получение 3 случайных непрочитанных тем
def get_random_unread_topics(user_id: str, level: str) -> list:
    topics_resp = supabase.from_("topics_by_level").select("topic").eq("level", level).execute()
    all_topics = [row["topic"] for row in topics_resp.data]

    read_resp = supabase.from_("user_topics").select("topic").eq("user_id", user_id).execute()
    read_topics = [row["topic"] for row in read_resp.data] if read_resp.data else []

    unread_topics = [topic for topic in all_topics if topic not in read_topics]
    random.shuffle(unread_topics)
    return unread_topics[:3]

# Получить 3 темы
@router.post("/get_topics")
async def get_topics(request: TopicRequest):
    try:
        log_message("Запрос get_topics от user_id", request.user_id)

        user_response = supabase.from_("users_progress").select("level").eq("user_id", request.user_id).maybe_single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        user_level = user_response.data["level"]

        new_topics = get_random_unread_topics(request.user_id, user_level)
        if not new_topics:
            return {"topics": [], "message": "Нет непрочитанных тем"}

        return {"topics": new_topics}

    except Exception as e:
        log_message("Ошибка в get_topics", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

# Генерация статьи
@router.post("/generate_article")
async def generate_article(request: GenerateArticleRequest):
    try:
        log_message("Запрос на генерацию статьи", request.dict())

        # Проверка — статья уже существует?
        existing_article_resp = supabase.from_("user_topics") \
            .select("content") \
            .eq("user_id", request.user_id) \
            .eq("topic", request.topic) \
            .maybe_single() \
            .execute()

        if existing_article_resp and existing_article_resp.data:
            content = existing_article_resp.data.get("content")
            if content:
                return {"article": content}

        # Получаем уровень пользователя
        user_response = supabase.from_("users_progress").select("level").eq("user_id", request.user_id).maybe_single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        user_level = user_response.data["level"]

        # Генерация статьи
        prompt = f"""
        Write an academic IELTS Reading-style article on the topic: "{request.topic}".
        Requirements:
        - Length: 250–300 words
        - Formal academic tone
        - Structured in paragraphs
        - No questions or bullet points
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an IELTS Reading assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        article_text = response["choices"][0]["message"]["content"].strip()

        # Сохраняем статью
        supabase.from_("user_topics").upsert({
            "user_id": request.user_id,
            "topic": request.topic,
            "content": article_text,
            "read": False,
            "level": user_level,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        return {"article": article_text}

    except Exception as e:
        log_message(" Ошибка в generate_article", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

# Пометить тему как прочитанную
@router.post("/mark_as_read")
async def mark_as_read(request: MarkAsReadRequest):
    try:
        log_message("Пометка темы как прочитанной", request.dict())
        supabase.from_("user_topics") \
            .update({
                "read": True,
                "updated_at": datetime.utcnow().isoformat()
            }) \
            .eq("user_id", request.user_id) \
            .eq("topic", request.topic) \
            .execute()
        return {"status": "marked as read"}
    except Exception as e:
        log_message("Ошибка в mark_as_read", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

# Получить историю прочитанного
@router.post("/get_history")
async def get_history(request: HistoryRequest):
    try:
        log_message("Запрос истории прочитанных тем", request.dict())

        response = supabase.from_("user_topics") \
            .select("topic, content, read, level, updated_at") \
            .eq("user_id", request.user_id) \
            .eq("read", True) \
            .order("updated_at", desc=True) \
            .execute()

        if not response.data:
            return {"history": [], "message": "История пуста"}

        return {"history": response.data}

    except Exception as e:
        log_message("Ошибка в get_history", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
