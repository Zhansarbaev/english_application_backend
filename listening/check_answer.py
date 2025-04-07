import os
import json
import re
import openai
from supabase import create_client
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY


router = APIRouter()


class AnswerRequest(BaseModel):
    user_id: str
    answers: List[str]
    topic: str

# Функция для исправления JSON, если он обрезан
def fix_broken_json(response_text: str) -> str:
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if match:
        fixed_json = match.group(0)
        if not fixed_json.endswith("}"):
            fixed_json += "}"
        return fixed_json
    return ""

@router.post("/check_answer")
async def check_answer(request: AnswerRequest):
    # Проверяем, есть ли 3 ответа
    if len(request.answers) != 3:
        raise HTTPException(status_code=400, detail="Нужно 3 ответа")

    # Получаем последние 3 транскрипции пользователя
    data_resp = (
        supabase.from_("user_transcripts")
        .select("id, podcast_title, transcript, topic, created_at")
        .eq("user_id", request.user_id)
        .eq("topic", request.topic)
        .order("created_at", desc=True)  # Берем последние 3
        .limit(3)
        .execute()
    )

    transcripts = [
        (item["id"], item["podcast_title"], item["transcript"])
        for item in data_resp.data
    ]

    if len(transcripts) < 3:
        raise HTTPException(status_code=404, detail="Нет 3 подкастов по теме")

    evaluation_results = []

    for i in range(3):
        transcript_id, podcast_title, transcript = transcripts[i]
        answer = request.answers[i]

        # Строгий Prompt для OpenAI (только JSON)
        system_prompt = (
            "Сен тек JSON форматында жауап беретін көмекшісің. "
            "Қазақ тілінде сөйлейсің. Артық мәтін немесе түсініктеме жазба. "
            "JSON форматы: {\"correct\": true/false, \"feedback\": \"...\"}."
            "Егер JSON бере алмасаң, осылай қайтар: {\"correct\": false, \"feedback\": \"\"}."
        )
        user_prompt = (
            f"Пайдаланушы жауабы: {answer}\n"
            "Осы жауап дұрыс па, әлде толық емес пе? "
            "Тек JSON форматында жауап бер, мысалы: {\"correct\": false, \"feedback\": \"Жауап толық емес\"}."
        )

        # Отправляем запрос в OpenAI
        try:
            gpt_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,  
                temperature=0
            )
        except openai.error.OpenAIError as e:
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

        raw_text = gpt_response["choices"][0]["message"]["content"]
        print(f"GPT raw: {raw_text}")  # Логируем реальный ответ от GPT

        # Пытаемся распарсить JSON
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            # Если JSON сломан пробую исправить
            fixed = fix_broken_json(raw_text)
            if fixed:
                try:
                    result = json.loads(fixed)
                except:
                    result = {"correct": False, "feedback": ""}
            else:
                result = {"correct": False, "feedback": ""}

        correct = result.get("correct", False)
        feedback = result.get("feedback", "")

        # Обновляем `success` ТОЛЬКО у последних 3 записей
        supabase.from_("user_transcripts").update({"success": correct}).eq("id", transcript_id).execute()

        evaluation_results.append({
            "podcast_title": podcast_title,
            "message": feedback,
            "success": correct
        })

    # 5. Возвращаем JSON-ответ
    return JSONResponse({"evaluations": evaluation_results})
