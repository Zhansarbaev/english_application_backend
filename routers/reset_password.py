import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime, timedelta
import jwt
from fastapi.responses import FileResponse

# Загружаем переменные из .env
load_dotenv()

# Настройки из .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Создаём клиента Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Настройка email через переменные окружения
class EmailConfig:
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 465))
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_STARTTLS = False  # Для Yandex обычно False
    MAIL_SSL_TLS = True    # Используем SSL/TLS

conf = ConnectionConfig(
    MAIL_USERNAME=EmailConfig.MAIL_USERNAME,
    MAIL_PASSWORD=EmailConfig.MAIL_PASSWORD,
    MAIL_FROM=EmailConfig.MAIL_FROM,
    MAIL_PORT=EmailConfig.MAIL_PORT,
    MAIL_SERVER=EmailConfig.MAIL_SERVER,
    MAIL_STARTTLS=EmailConfig.MAIL_STARTTLS,
    MAIL_SSL_TLS=EmailConfig.MAIL_SSL_TLS
)

router = APIRouter()

# Модель для запроса сброса пароля (принимает только email)
class ForgotPasswordRequest(BaseModel):
    email: str

# Модель для запроса сброса пароля с токеном и новым паролем
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Функция генерации JWT-токена (действителен 1 час)
def create_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(hours=1)
    token = jwt.encode({"sub": email, "exp": expire}, JWT_SECRET_KEY, algorithm="HS256")
    return token

# Функция отправки email с токеном
async def send_reset_email(email: str, token: str):
    # Замените этот URL на ваш реальный ngrok или доменный URL
    reset_link = f"https://34ff-79-140-224-173.ngrok-free.app/password/reset-password?token={token}"
    message = MessageSchema(
        subject="App English қосымшасы - Аккаунтың құпиясөзін қалпына келтіру",
        recipients=[email],
        body=f"Құпиясөзді қалпына келтіру үшін келесі сілтемеге өтіңіз: {reset_link}",
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

# Маршрут для запроса сброса пароля (отправка email)
@router.post("/forgot/")
async def forgot_password(request: ForgotPasswordRequest):
    email = request.email
    if not email:
        raise HTTPException(status_code=400, detail="Email міндетті")
    token = create_reset_token(email)
    await send_reset_email(email, token)
    return {"message": "Сілтеме жіберілді"}

# Маршрут для изменения пароля (обновление в Supabase)
@router.post("/reset-password/")
async def reset_password(request: ResetPasswordRequest):
    try:
        # Декодируем токен и получаем email
        token_data = jwt.decode(request.token, JWT_SECRET_KEY, algorithms=["HS256"])
        email = token_data.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Неверный токен")
        
        # Получаем всех пользователей (метод list_users() возвращает список объектов)
        all_users = supabase.auth.admin.list_users()
        # Фильтруем пользователей по email
        matching_users = [user for user in all_users if hasattr(user, "email") and user.email == email]
        if not matching_users:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        uid = matching_users[0].id
        
        # Обновляем пароль в Supabase, передавая данные как словарь
        supabase.auth.admin.update_user_by_id(uid, {"password": request.new_password})
        
        return {"message": "Пароль успешно изменен"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Токен истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Неверный токен")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# Маршрут для отображения HTML-страницы сброса пароля (возвращает index.html)
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(token: str):
    try:
        token_data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        email = token_data.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Неверный токен")
        
        # Читаем содержимое файла index.html (убедитесь, что он находится в той же директории)
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return html_content
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Токен истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Неверный токен")
