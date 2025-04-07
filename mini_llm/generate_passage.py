import openai
import pandas as pd 
import json
from tqdm import tqdm
import time
from dotenv import load_dotenv
import os

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=r"C:\app_english_back\.env")  

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY 


df = pd.read_csv(r"C:\app_english_back\mini_llm\IELTS_Reading_Topics.csv")
topics = df["IELTS Reading Topics"].tolist() # Преобразуем series в пандасе в лист для питона

def build_prompt(topic):
    return f"""
You are an IELTS Reading passage generator.
Write a reading passage of about 350-400 words based on the following topic:
{topic}

Requirements:
- Use academic language suitable for IELTS.
- Structure the passage into 3 paragraphs.
- Avoid giving personal opinions.
- Include a title.


"""

def generate_passage(topic):
    prompt = build_prompt(topic)
    try:
        response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": "You are an IELTS academic text generator."},
                {"role": "user", "content": prompt}

            ],
            temperature = 0.7,
            max_tokens = 600,

        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error for topic '{topic}': {e}")
        return None

with open("ielts_dataset.jsonl", "w", encoding = "utf-8") as f_out:
    for topic in tqdm(topics[:10]):
        text = generate_passage(topic)
        if text:
            item = {
                "prompt": f"Write an IELTS Reading passage about: {topic}",
                "response": text
            }
            f_out.write(json.dumps(item, ensure_ascii = False) + "\n")
            time.sleep(1.2)