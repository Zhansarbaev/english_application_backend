from fastapi import FastAPI, HTTPException, APIRouter
import os
from dotenv import load_dotenv
from typing import Dict
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.get("/user/{user_id}/stats")
async def get_user_stats(user_id: str) -> Dict:
    try:
        user_response = supabase.table("users_basic").select("email").eq("id", user_id).single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        email = user_response.data["email"]

        user_progress_response = supabase.table("users_progress").select("level, unlocked_level").eq("user_id", user_id).single().execute()
        if not user_progress_response.data:
            raise HTTPException(status_code=404, detail="User progress not found")

        level = user_progress_response.data["level"]
        unlocked_level = user_progress_response.data["unlocked_level"]

        vocab_total = len(supabase.table("vocabulary_super").select("*").eq("level", level).execute().data)
        vocab_learned = len(supabase.table("user_vocabulary_progress").select("*").eq("user_id", user_id).eq("is_read", True).execute().data)

        listening_sessions = len(supabase.table("user_transcripts").select("*").eq("user_id", user_id).eq("success", True).execute().data)

        reading_total = len(supabase.table("topics_by_level").select("*").eq("level", level).execute().data)
        reading_read = len(supabase.table("user_topics").select("*").eq("user_id", user_id).eq("level", level).eq("read", True).execute().data)

        return {
            "user": {
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

# Инициализация приложения
app = FastAPI()

app.include_router(router, prefix="/statistic", tags=["Statistic"])

@app.get("/")
def root():
    return {"message": "FastAPI сервер работает!"}
