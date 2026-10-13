import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
TIMEOUT = int(os.getenv("TIMEOUT", "5"))
DB_PASSWORD = os.getenv("DB_PASSWORD")