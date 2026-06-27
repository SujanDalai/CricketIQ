class WeatherAPI:
    """
    Wrapper for Weather API to fetch current conditions and forecasts for match venues.
    """
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url

    def get_weather(self, city: str):
        # TODO: Implement API requests
        pass
