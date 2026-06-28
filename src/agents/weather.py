from src.agents.base import BaseAgent
from src.tools.weather_api import WeatherAPI
from src.tools.cricket_data import PITCH_CONDITIONS
from src.config import Config

VENUE_TO_CITY = {
    "perth": "Perth,AU",
    "mumbai": "Mumbai,IN",
    "lord's": "London,GB",
    "edgbaston": "Birmingham,GB",
    "sydney": "Sydney,AU",
    "melbourne": "Melbourne,AU",
    "delhi": "Delhi,IN",
    "birmingham": "Birmingham,GB",
}


class WeatherAgent(BaseAgent):
    """
    Weather Agent fetches and interprets meteorological data for specific
    locations to evaluate match feasibility and pitch/conditions impact.
    """
    def __init__(self):
        super().__init__(name="WeatherAgent", role="Weather Forecasting and Impact Analysis")
        self.config = Config()
        self.weather_api = WeatherAPI(self.config.WEATHER_API_KEY, self.config.WEATHER_API_URL)

    def _find_venue(self, task_lower: str):
        for venue in PITCH_CONDITIONS.keys():
            if venue in task_lower:
                return venue
        return None

    def run(self, task: str) -> str:
        task_lower = task.lower()
        venue = self._find_venue(task_lower)

        if not venue:
            return "WeatherAgent: Could not identify venue in task."

        weather = self.weather_api.get_weather(VENUE_TO_CITY.get(venue, venue))

        if "error" in weather:
            return f"WeatherAgent: Unable to fetch weather for {venue.title()} ({weather['error']})"

        impact = []
        if weather["humidity_pct"] > 70:
            impact.append("high humidity may assist swing bowlers")
        if weather["wind_speed_mps"] > 5:
            impact.append("breezy conditions could aid seam movement")
        if weather["condition"].lower() in ("rain", "thunderstorm"):
            impact.append("possible rain delay risk")

        impact_text = "; ".join(impact) if impact else "no significant weather impact expected"

        return f"""
=== WEATHER ANALYSIS: {venue.title()} ===
Temperature   : {weather['temperature_c']}°C (feels like {weather['feels_like_c']}°C)
Humidity      : {weather['humidity_pct']}%
Wind Speed    : {weather['wind_speed_mps']} m/s
Condition     : {weather['condition']} ({weather['description']})

IMPACT ANALYSIS:
{impact_text}
"""