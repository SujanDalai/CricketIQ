from src.tools.cric_api import CricAPI
from src.tools.weather_api import WeatherAPI
from src.config import Config


def test_cric_api():
    c = Config()
    api = CricAPI(c.CRIC_API_KEY)
    result = api.get_live_scores()
    print("CricAPI result:", result)
    assert result is not None


def test_weather_api():
    c = Config()
    api = WeatherAPI(c.WEATHER_API_KEY, c.WEATHER_API_URL)
    result = api.get_weather("London,GB")
    print("WeatherAPI result:", result)
    assert "error" not in result