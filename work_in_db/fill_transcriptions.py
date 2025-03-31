import os
import openai
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# Загружаем переменные окружения
load_dotenv()

# Ключи из .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Подключаемся к Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

# ⚡ Получаем слово без транскрипции
def fetch_word_without_transcription():
    response = supabase.table("vocabulary_super").select("id, word").is_("transcription", None).limit(1).execute()
    return response.data[0] if response.data else None

# ⚡ Обновляем транскрипцию в базе
def update_transcription(word_id, transcription):
    supabase.table("vocabulary_super").update({"transcription": transcription}).eq("id", word_id).execute()

# ⚡ Запрашиваем транскрипцию с форматом в [скобках]
def get_transcription(word):
    prompt = f"Дай только IPA-транскрипцию слова {word} в квадратных скобках. Пример: [teɪbl]"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Используем дешевую и быструю модель
            messages=[{"role": "user", "content": prompt}],
            temperature=0  # Убираем случайные вариации
        )
        transcription = response["choices"][0]["message"]["content"].strip()

        # Проверяем, что ответ содержит [ ], если нет — добавляем
        if not transcription.startswith("[") or not transcription.endswith("]"):
            transcription = f"[{transcription}]"

        return transcription
    except Exception as e:
        print(f"❌ Ошибка OpenAI: {e}")
        return None

# ⚡ Основной процесс (ускоренная обработка по 1 слову)
def main():
    start_time = time.time()
    processed_count = 0

    while True:
        word_data = fetch_word_without_transcription()
        if not word_data:
            print(f"✅ Все слова обработаны! Обработано: {processed_count} слов")
            break

        word_id = word_data["id"]
        word = word_data["word"]

        print(f"🔹 Обрабатываем: {word}...")
        transcription = get_transcription(word)

        if transcription:
            update_transcription(word_id, transcription)
            processed_count += 1
            print(f"✅ {word}: {transcription}")
        else:
            print(f"❌ Ошибка для {word}")

        time.sleep(0.2)  # Уменьшенная пауза для ускорения

    elapsed_time = time.time() - start_time
    print(f"⏳ Время выполнения: {elapsed_time:.2f} сек (~{elapsed_time/60:.2f} мин)")

if __name__ == "__main__":
    main()
