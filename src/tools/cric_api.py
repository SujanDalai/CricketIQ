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
        result = self._get("players", params={"offset": 0, "search": player_name})
        if "error" in result:
            return result
        return result.get("data", [])

    def get_player_stats(self, player_name: str) -> dict:
        """
        Search for a player by name, fetch their full stats (batting + bowling),
        and return a clean structured dict ready for the agents to use.
        """
        major_nations = {
            "india", "australia", "england", "pakistan", "new zealand",
            "south africa", "west indies", "sri lanka", "bangladesh",
            "zimbabwe", "afghanistan", "ireland"
        }

        # Step 1: search with pagination across 3 pages
        best = None
        for offset in [0, 25, 50]:
            search_result = self._get("players", params={"offset": offset, "search": player_name})
            if "error" in search_result:
                break

            players = search_result.get("data", [])
            for p in players:
                name_match = player_name.lower() in p.get("name", "").lower()
                country = p.get("country", "").lower()
                if name_match and country in major_nations:
                    best = p
                    break

            if best:
                break

        # Fallback — try last name only
        if not best:
            parts = player_name.strip().split()
            if len(parts) > 1:
                fallback = self._get("players", params={"offset": 0, "search": parts[-1]})
                players = fallback.get("data", []) if "error" not in fallback else []
                for p in players:
                    if player_name.lower() in p.get("name", "").lower() and p.get("country", "").lower() in major_nations:
                        best = p
                        break

        if not best:
            return {"error": f"No player found for '{player_name}'"}

        player_id = best["id"]
        player_name_official = best["name"]

        # Step 2: fetch full player info
        info_result = self._get("players_info", params={"id": player_id})
        if "error" in info_result:
            return {"error": info_result["error"]}

        data = info_result.get("data", {})
        stats = data.get("stats", [])

        # Step 3: parse batting stats
        batting_parsed = {}
        for s in stats:
            matchtype = s.get("matchtype")
            stat = s.get("stat")
            value = s.get("value")
            fn = s.get("fn")

            if fn != "batting":
                continue
            if matchtype not in ("test", "odi", "t20i"):
                continue
            if stat and stat.strip() != stat:
                continue

            if matchtype not in batting_parsed:
                batting_parsed[matchtype] = {}
            batting_parsed[matchtype][stat] = value

        # Step 4: parse bowling stats
        bowling_parsed = {}
        for s in stats:
            matchtype = s.get("matchtype")
            stat = s.get("stat")
            value = s.get("value")
            fn = s.get("fn")

            if fn != "bowling":
                continue
            if matchtype not in ("test", "odi", "t20i"):
                continue
            if stat and stat.strip() != stat:
                continue

            if matchtype not in bowling_parsed:
                bowling_parsed[matchtype] = {}
            bowling_parsed[matchtype][stat] = value

        return {
            "name": player_name_official,
            "country": data.get("country"),
            "role": data.get("role"),
            "dob": data.get("dateOfBirth", "")[:10],
            "batting_stats": batting_parsed,
            "bowling_stats": bowling_parsed,
        }