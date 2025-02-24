from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# Модель запроса
class UnlockRequest(BaseModel):
    user_id: str

@router.post("/listening/unlock_card")
async def unlock_new_card(request: UnlockRequest):
    try:
        # Получаем уровень пользователя и его `unlocked_level`
        user_progress = supabase.from_("users_progress").select("level").eq("user_id", request.user_id).single().execute()


        if not user_progress.data:
            raise HTTPException(status_code=404, detail="Пайдаланушы табылған жоқ.")

        user_level = user_progress.data["level"]
        unlocked_level = user_progress.data["unlocked_level"]

        # Проверяем, есть ли следующая карточка
        next_card = (
            supabase.from_("vocabulary_super")
            .select("id")
            .eq("level", user_level)
            .eq("unlocked_level", unlocked_level + 1)
            .maybe_single()
            .execute()
        )

        if not next_card.data:
            return {"message": "🔓 Барлық карточкалар ашық!"}

        # Обновляем `unlocked_level`
        supabase.from_("users_progress").update({"unlocked_level": unlocked_level + 1}).eq("user_id", request.user_id).execute()

        return {"message": "✅ Жаңа сөз ашылды!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Қате: {str(e)}")
