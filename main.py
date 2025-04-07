from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
  
# 🔹 Импортируем роутеры
from routers import reset_password
from listening.unlock_card import router as unlock_router
from listening.check_answer import router as check_answer_router
from listening.podcasts_api import router as podcasts_router
from listening.video_api import router as videos_router
from listening.speech_to_text import router as speech_router
from reading.article import router as article_router
from reading.article import router as article_router
from statistic_for_user.statistic import router as statistic_user

app = FastAPI()

# 🔹 Раздаём статические файлы из папки /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔹 Раздаём иконку (favicon) из /static
@app.get("/password_icon.png", include_in_schema=False)
async def favicon():
    return FileResponse("static/password_icon.png")

# 🔹 Добавляем CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
  # Можно указать конкретные домены вместо "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Подключаем все маршруты
app.include_router(reset_password.router, prefix="/password", tags=["Password"])
app.include_router(unlock_router, prefix="/listening", tags=["Unlock Card"])
app.include_router(check_answer_router, prefix="/listening", tags=["Check Answer"])
app.include_router(podcasts_router, prefix="/listening", tags=["Podcasts"])
app.include_router(videos_router, prefix="/listening", tags=["Videos"])
app.include_router(speech_router, prefix="/listening", tags=["Speech"])
app.include_router(article_router, prefix="/reading", tags=["Reading"])
app.include_router(article_router, prefix="/reading", tags=["Reading"])
app.include_router(statistic_user, prefix="/statistic", tags=["Statistic"])

@app.get("/")
def root():
    return {"message": "FastAPI сервер работает!"}
