from src.agents.base import BaseAgent
from src.tools.weather_api import WeatherAPI
from src.tools.cricket_data import PITCH_CONDITIONS
from src.config import Config

VENUE_TO_CITY = {
    # England
    "lord's": "London,GB",
    "old trafford": "Manchester,GB",
    "edgbaston": "Birmingham,GB",
    "the oval": "London,GB",
    "trent bridge": "Nottingham,GB",
    "headingley": "Leeds,GB",
    "rose bowl": "Southampton,GB",
    
    # Australia
    "mcg": "Melbourne,AU",
    "scg": "Sydney,AU",
    "perth stadium": "Perth,AU",
    "adelaide oval": "Adelaide,AU",
    "the gabba": "Brisbane,AU",
    "waca": "Perth,AU",
    
    # India
    "wankhede": "Mumbai,IN",
    "arun jaitley stadium": "Delhi,IN",
    "eden gardens": "Kolkata,IN",
    "narendra modi stadium": "Ahmedabad,IN",
    "m.a. chidambaram": "Chennai,IN",
    "rajiv gandhi international": "Hyderabad,IN",
    "delhi": "Delhi,IN",
    "mumbai": "Mumbai,IN",
    
    # South Africa
    "the wanderers": "Johannesburg,ZA",
    "newlands": "Cape Town,ZA",
    "kingsmead": "Durban,ZA",
    
    # West Indies
    "sabina park": "Kingston,JM",
    "queen's park oval": "Port of Spain,TT",
    
    # Pakistan
    "gaddafi stadium": "Lahore,PK",
    "national stadium": "Karachi,PK",
    "rawalpindi stadium": "Rawalpindi,PK",
    
    # New Zealand
    "basin reserve": "Wellington,NZ",
    "eden park": "Auckland,NZ",
    "whangarei": "Whangarei,NZ",
    
    # Generic fallbacks (for old data)
    "perth": "Perth,AU",
    "sydney": "Sydney,AU",
    "melbourne": "Melbourne,AU",
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
