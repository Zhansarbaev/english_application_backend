import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API")
GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


class TranslateRequest(BaseModel):
    word: str
    target_lang: str = "kk"  # по умолчанию перевод на казахский


@router.post("/translate_google")
async def translate_google(request: TranslateRequest):
    if not GOOGLE_TRANSLATE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API ключ не найден")

    try:
        response = requests.post(
            GOOGLE_TRANSLATE_URL,
            params={"key": GOOGLE_TRANSLATE_API_KEY},
            json={
                "q": request.word,
                "target": request.target_lang,
                "format": "text",
                "source": "en",
            },
        )
        response.encoding = 'utf-8'
        data = response.json()

        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"]["message"])

        translation = data["data"]["translations"][0]["translatedText"]
        return {"translation": translation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка перевода: {e}")


