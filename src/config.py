import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CRIC_API_KEY      = os.getenv("CRIC_API_KEY", "")
    WEATHER_API_KEY   = os.getenv("WEATHER_API_KEY", "")
    WEATHER_API_URL   = os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5/weather")
    GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")

    # Keep this for reference but we no longer call ollama directly
    OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")