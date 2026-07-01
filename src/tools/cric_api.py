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
    def get_player_stats(self, player_name: str) -> dict:
        """
        Search for a player by name, fetch their full stats,
        and return a clean structured dict ready for the agents to use.
        """
        # Step 1: search for player to get their ID
        search_result = self._get("players", params={"offset": 0, "search": player_name})
        if "error" in search_result:
            return {"error": search_result["error"]}

        players = search_result.get("data", [])
        if not players:
            return {"error": f"No player found for '{player_name}'"}

        player_id = players[0]["id"]
        player_name_official = players[0]["name"]

        # Step 2: fetch full player info
        info_result = self._get("players_info", params={"id": player_id})
        if "error" in info_result:
            return {"error": info_result["error"]}

        data = info_result.get("data", {})
        stats = data.get("stats", [])

        # Step 3: parse stats into a clean nested dict
        # Structure: parsed[matchtype][stat] = value
        parsed = {}
        for s in stats:
            matchtype = s.get("matchtype")
            stat = s.get("stat")
            value = s.get("value")
            fn = s.get("fn")

            if fn != "batting":
                continue
            if matchtype not in ("test", "odi", "t20i"):
                continue

            if matchtype not in parsed:
                parsed[matchtype] = {}
            parsed[matchtype][stat] = value

        return {
            "name": player_name_official,
            "country": data.get("country"),
            "role": data.get("role"),
            "dob": data.get("dateOfBirth", "")[:10],
            "batting_stats": parsed,
        }