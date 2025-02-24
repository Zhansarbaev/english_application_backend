import os
import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# 🔹 Загружаем переменные окружения
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

# 🔹 Модель запроса
class AnswerRequest(BaseModel):
    user_id: str
    answer: str

@router.post("/listening/check_answer")
async def check_answer(request: AnswerRequest):
    try:
        # 🔹 Формируем запрос к GPT
        prompt = (
            f"Пользователь дал следующий ответ на прослушанный текст: \"{request.answer}\". "
            f"Верный ли этот ответ по смыслу? "
            f"Ответь только одним словом: 'да' или 'нет'."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Можно заменить на "gpt-4o-mini" если экономишь
            messages=[{"role": "user", "content": prompt}]
        )

        # 🔹 GPT ответит "да" или "нет"
        ai_response = response["choices"][0]["message"]["content"].strip().lower()

        if "да" in ai_response:
            return {"message": "✅ Жауап дұрыс!", "success": True}
        elif "нет" in ai_response:
            return {"message": "❌ Қате жауап! Қайта көріңіз.", "success": False}
        else:
            return {"message": "⚠ GPT жауапты түсінбеді. Қайта көріңіз.", "success": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT қатесі: {str(e)}")
