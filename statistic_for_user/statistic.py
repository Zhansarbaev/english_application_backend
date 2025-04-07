from fastapi import FastAPI, HTTPException, APIRouter
import os
from dotenv import load_dotenv
from typing import Dict
from supabase import create_client, Client
import logging


logging.basicConfig(level=logging.DEBUG)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.get("/user/{user_id}/stats")
async def get_user_stats(user_id: str) -> Dict:
    try:
        logging.debug(f"Запрос статистики для пользователя {user_id}")

        # Получение email из view
        user_response = supabase.table("users_basic").select("email").eq("id", user_id).single().execute()
        logging.debug(f"Ответ на запрос email: {user_response}")
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        email = user_response.data["email"]

        # Получение уровня и unlocked уровня
        user_progress_response = supabase.table("users_progress").select("level, unlocked_level").eq("user_id", user_id).single().execute()
        logging.debug(f"Ответ на запрос прогресса: {user_progress_response}")
        if not user_progress_response.data:
            raise HTTPException(status_code=404, detail="User progress not found")

        level = user_progress_response.data["level"]
        unlocked_level = user_progress_response.data["unlocked_level"]

        # Vocabulary 
        vocab_total_response = supabase.table("vocabulary_super").select("*").eq("level", level).execute()
        vocab_total = len(vocab_total_response.data)
        logging.debug(f"Общее количество слов: {vocab_total}")

        vocab_learned_response = supabase.table("user_vocabulary_progress").select("*").eq("user_id", user_id).eq("is_read", True).execute()
        vocab_learned = len(vocab_learned_response.data)
        logging.debug(f"Количество выученных слов: {vocab_learned}")

        # Listening
        listening_sessions_response = supabase.table("user_transcripts").select("*").eq("user_id", user_id).eq("success", True).execute()
        listening_sessions = len(listening_sessions_response.data)
        logging.debug(f"Количество успешных сессий слушания: {listening_sessions}")

        # Reading
        reading_total_response = supabase.table("topics_by_level").select("*").eq("level", level).execute()
        reading_total = len(reading_total_response.data)
        logging.debug(f"Общее количество тем: {reading_total}")

        reading_read_response = supabase.table("user_topics").select("*").eq("user_id", user_id).eq("level", level).eq("read", True).execute()
        reading_read = len(reading_read_response.data)
        logging.debug(f"Количество прочитанных тем: {reading_read}")

        return {
            "user":{
                "email": email,
                "level": level,
                "unlocked_level": unlocked_level
            },
            "vocabulary": {
                "total": vocab_total,
                "learned": vocab_learned
            },
            "listening": {
                "total_sessions": listening_sessions
            },
            "reading": {
                "total_topics": reading_total,
                "read": reading_read
            }
        }

    except Exception as e:
        logging.error(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


app = FastAPI()


app.include_router(router, prefix="/statistic", tags=["Statistic"])

@app.get("/")
def root():
    return {"message": "FastAPI сервер работает!"}
