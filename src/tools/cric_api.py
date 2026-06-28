import requests


class CricAPI:
    """
    Wrapper for CricAPI (cricapi.com) endpoints to fetch live scores,
    schedules, and player info.
    """
    BASE_URL = "https://api.cricapi.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, endpoint: str, params: dict = None):
        if not self.api_key:
            return {"error": "No CRIC_API_KEY configured"}

        url = f"{self.BASE_URL}/{endpoint}"
        request_params = {"apikey": self.api_key}
        if params:
            request_params.update(params)

        try:
            response = requests.get(url, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                return {"error": data.get("reason", "Unknown API error")}

            return data
        except requests.exceptions.RequestException as e:
            return {"error": f"CricAPI request failed: {str(e)}"}

    def get_live_scores(self):
        """
        Fetch currently live cricket matches.
        Returns a list of match summaries, or an error dict.
        """
        result = self._get("currentMatches", params={"offset": 0})
        if "error" in result:
            return result

        matches = result.get("data", [])
        live_matches = [m for m in matches if m.get("matchStarted") and not m.get("matchEnded")]

        return [
            {
                "name": m.get("name"),
                "status": m.get("status"),
                "venue": m.get("venue"),
                "date": m.get("date"),
                "teams": m.get("teams"),
                "score": m.get("score"),
            }
            for m in live_matches
        ]

    def get_match_schedule(self):
        """
        Fetch upcoming match schedule.
        Returns a list of upcoming matches, or an error dict.
        """
        result = self._get("currentMatches", params={"offset": 0})
        if "error" in result:
            return result

        matches = result.get("data", [])
        upcoming = [m for m in matches if not m.get("matchStarted")]

        return [
            {
                "name": m.get("name"),
                "venue": m.get("venue"),
                "date": m.get("date"),
                "teams": m.get("teams"),
            }
            for m in upcoming
        ]

    def search_player(self, player_name: str):
        """
        Search for a player by name. Returns matching player info.
        """
        result = self._get("players", params={"offset": 0, "search": player_name})
        if "error" in result:
            return result
        return result.get("data", [])