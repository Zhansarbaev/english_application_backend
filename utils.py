import jwt
import datetime
from settings import JWT_SECRET_KEY

# 📌 Генерация JWT токена (для сброса пароля)
def create_reset_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)  # Токен живёт 30 минут
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token

# 📌 Проверка токена
def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        return None  # Ошибка: токен просрочен
    except jwt.InvalidTokenError:
        return None  # Ошибка: токен некорректен
