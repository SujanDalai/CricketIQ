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


@patch("src.tools.cricbuzz.requests.get")
def test_cricbuzz_scraper(mock_get):
    from src.tools.cricbuzz import CricbuzzScraper
    # Mocking the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.apparent_encoding = "utf-8"
    mock_response.text = """
    <html>
    <body>
    <a class="w-full bg-cbWhite flex flex-col p-3 gap-1" href="/live-cricket-scores/129574/nz-vs-eng-3rd-test-new-zealand-tour-of-england-2026" title="New Zealand vs England, 3rd Test ">
     <div class="flex justify-between items-center">
      <span class="text-xs text-cbTxtSec dark:text-cbTxtSec w-4/5">
       3rd Test • Nottingham, Trent Bridge
      </span>
     </div>
     <div class="flex flex-col gap-3 my-2">
      <div class="flex items-center gap-4 justify-between">
       <div class="flex items-center gap-2">
        <span class="text-cbTxtPrim dark:text-cbWhite hidden wb:block truncate">New Zealand</span>
       </div>
       <span class="font-medium wb:font-semibold text-cbTxtPrim dark:text-cbWhite w-1/2 truncate">438 &amp; 288-9 d</span>
      </div>
      <div class="flex items-center gap-4 justify-between">
       <div class="flex items-center gap-2">
        <span class="text-cbTxtSec dark:text-cbTxtSec hidden wb:block truncate">England</span>
       </div>
       <span class="font-medium wb:font-semibold text-cbTxtSec dark:text-cbTxtSec w-1/2 truncate">354 &amp; 212</span>
      </div>
     </div>
     <span class="text-cbComplete dark:text-cbCompleteDark">New Zealand won by 160 runs</span>
    </a>
    </body>
    </html>
    """
    mock_get.return_value = mock_response

    scraper = CricbuzzScraper()
    live_scores = scraper.get_live_scores()
    
    assert len(live_scores) == 1
    match = live_scores[0]
    assert match["name"] == "New Zealand vs England, 3rd Test"
    assert match["venue"] == "3rd Test - Nottingham, Trent Bridge"
    assert match["status"] == "New Zealand won by 160 runs"
    assert match["date"] == "Completed"
    assert match["teams"] == ["New Zealand", "England"]
    assert match["score"] == "New Zealand 438 & 288-9 d vs England 354 & 212"
