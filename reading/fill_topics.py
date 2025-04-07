import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


df = pd.read_csv(r"C:\app_english_back\reading\ielts_reading_topics_by_level.csv")  


for row in df.to_dict(orient="records"):
    response = supabase.table("topics_by_level").insert(row).execute()
    print("Добавляю:", row)
