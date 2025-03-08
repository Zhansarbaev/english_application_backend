from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# Указываем максимальный `unlocked_level`
MAX_UNLOCK_LEVEL = 3  # Не уйдет выше 3


class UnlockRequest(BaseModel):
    user_id: str

@router.post("/unlock_card")
async def unlock_new_card(request: UnlockRequest):
    try:
        #  1. Получаем текущий `unlocked_level`
        user_progress = supabase.from_("users_progress").select("level, unlocked_level").eq("user_id", request.user_id).single().execute()
        
        if not user_progress.data:
            raise HTTPException(status_code=404, detail="Пайдаланушы табылған жоқ.")
        
        user_level = user_progress.data["level"]
        unlocked_level = user_progress.data["unlocked_level"]

        print(f"Пользователь: {request.user_id} | Уровень: {user_level} | Открытый уровень: {unlocked_level}")

        # 2. Если `unlocked_level` уже максимальный, то не увеличиваем
        if unlocked_level >= MAX_UNLOCK_LEVEL:
            return {"message": f"Сіз барлық карточкаларды аштыңыз! ({MAX_UNLOCK_LEVEL})"}

        # 3. Получаем последние 3 `success`
        response = (
            supabase.from_("user_transcripts")
            .select("success")
            .eq("user_id", request.user_id)
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        
        success_values = [item["success"] for item in response.data]

        print(f"Последние 3 `success` значения: {success_values}")

        # 4. Проверяем, все ли три ответа успешные (true)
        if len(success_values) == 3 and all(success_values):
            print("Все 3 ответа верные, открываем новую карточку!")

            # 5. Обновляем `unlocked_level` ТОЛЬКО если он < MAX_UNLOCK_LEVEL
            new_unlocked_level = min(unlocked_level + 1, MAX_UNLOCK_LEVEL)

            update_response = supabase.from_("users_progress").update({"unlocked_level": new_unlocked_level}).eq("user_id", request.user_id).execute()

            print(f" Обновлен `unlocked_level`: {new_unlocked_level} | Ответ от Supabase: {update_response}")

            return {"message": f"Жаңа карта ашылды! Сіздің жаңа деңгейіңіз: {new_unlocked_level}"}
        else:
            return {"message": "Сіз барлық сұрақтарға дұрыс жауап берген жоқсыз."}
    
    except Exception as e:
        print(f"Қате: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Қате: {str(e)}")
