from pydantic import BaseModel

# 📌 Модель для сброса пароля
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
