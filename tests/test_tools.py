from unittest.mock import patch, MagicMock
from src.tools.cric_api import CricAPI
from src.tools.weather_api import WeatherAPI
from src.config import Config


@patch("src.tools.cric_api.requests.get")
def test_cric_api(mock_get):
    # Mocking the HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "data": [
            {
                "name": "India vs Australia",
                "status": "Match started",
                "venue": "Perth Stadium",
                "date": "2026-06-28",
                "teams": ["India", "Australia"],
                "score": [],
                "matchStarted": True,
                "matchEnded": False
            }
        ]
    }
    mock_get.return_value = mock_response

    # Force a dummy key to avoid the 'No CRIC_API_KEY configured' check
    api = CricAPI("dummy_key")
    result = api.get_live_scores()
    print("CricAPI result:", result)
    
    assert result is not None
    assert len(result) == 1
    assert result[0]["name"] == "India vs Australia"


@patch("src.tools.weather_api.requests.get")
def test_weather_api(mock_get):
    # Mocking the HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "London",
        "main": {
            "temp": 15.0,
            "feels_like": 14.5,
            "humidity": 80
        },
        "wind": {
            "speed": 5.0
        },
        "weather": [
            {
                "main": "Rain",
                "description": "light rain"
            }
        ]
    }
    mock_get.return_value = mock_response

    # Force a dummy key and URL to avoid config check
    api = WeatherAPI("dummy_key", "https://api.openweathermap.org/data/2.5/weather")
    result = api.get_weather("London,GB")
    print("WeatherAPI result:", result)
    
    assert "error" not in result
    assert result["city"] == "London"
    assert result["temperature_c"] == 15.0
    assert result["condition"] == "Rain"