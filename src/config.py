import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CRIC_API_KEY = os.getenv("CRIC_API_KEY", "")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_URL = os.getenv(
        "WEATHER_API_URL",
        "https://api.openweathermap.org/data/2.5/weather"
    )
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "Groq")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")