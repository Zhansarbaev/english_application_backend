import asyncio
from fastapi_mail import FastMail, MessageSchema
from settings import conf

async def send_test_email():
    message = MessageSchema(
        subject="Тестовое письмо от FastAPI",
        recipients=["zhansarbaevvv@gmail.com"],  # Укажи email получателя
        body="Привет! Это тестовое письмо через Yandex SMTP (FastAPI).",
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    print("Email отправлен!")

# Запуск асинхронной функции
asyncio.run(send_test_email())
