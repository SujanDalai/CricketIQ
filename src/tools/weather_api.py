import requests


class WeatherAPI:
    """
    Wrapper for OpenWeatherMap API to fetch current conditions for match venues.
    """
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url

    def get_weather(self, city: str):
        """
        Fetch current weather for a given city.
        Returns a dict with temperature, humidity, wind speed, and conditions,
        or an error dict if the request fails.
        """
        if not self.api_key:
            return {"error": "No WEATHER_API_KEY configured"}

        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "city": data.get("name", city),
                "temperature_c": data["main"]["temp"],
                "feels_like_c": data["main"]["feels_like"],
                "humidity_pct": data["main"]["humidity"],
                "wind_speed_mps": data["wind"]["speed"],
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Weather API request failed: {str(e)}"}
        except (KeyError, IndexError) as e:
            return {"error": f"Unexpected weather API response format: {str(e)}"}