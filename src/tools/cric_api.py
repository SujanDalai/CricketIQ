import requests
import json
import time
from src.logger import logger

# Module-level cache — persists for the lifetime of the process
_PLAYER_CACHE: dict = {}
_PLAYER_ID_CACHE: dict = {}
_API_BLOCKED_UNTIL: float = 0.0

class CricAPI:
    """
    Wrapper for CricAPI (cricapi.com) endpoints to fetch live scores,
    schedules, and player info.
    """
    BASE_URL = "https://api.cricapi.com/v1"
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CricAPI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, api_key: str):
        if getattr(self, "_initialized", False) and self.api_key == api_key:
            return
        self.api_key = api_key
        self._initialized = True

    def _get(self, endpoint: str, params: dict = None):
        global _API_BLOCKED_UNTIL
        if time.time() < _API_BLOCKED_UNTIL:
            return {"error": "CricAPI rate limit reached: Blocked for 15 minutes", "rate_limit": True}

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
                reason = data.get("reason", "Unknown API error")
                if "Blocked for 15 minutes" in reason or "rate limit" in reason.lower() or "blocked" in reason.lower():
                    _API_BLOCKED_UNTIL = time.time() + 900  # block for 15 minutes
                    return {"error": f"CricAPI rate limit reached: {reason}", "rate_limit": True}
                return {"error": reason}

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
        # Check cache first
        cache_key = player_name.lower().strip()
        if cache_key in _PLAYER_CACHE:
            entry = _PLAYER_CACHE[cache_key]
            if time.time() - entry["timestamp"] < 3600:
                return entry["data"]

        player_id = _PLAYER_ID_CACHE.get(cache_key)
        player_name_official = None

        if not player_id:
            major_nations = {
                "india", "australia", "england", "pakistan", "new zealand",
                "south africa", "west indies", "sri lanka", "bangladesh",
                "zimbabwe", "afghanistan", "ireland"
            }

            # Step 1: search with pagination across 3 pages
            best = None
            for offset in [0, 25, 50]:
                search_result = self._get("players", params={"offset": offset, "search": player_name})
                logger.debug(f"SEARCHING: {player_name}")
                logger.debug(json.dumps(search_result, indent=2)[:3000])
                if "error" in search_result:
                    return search_result

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
                    if "error" in fallback:
                        return fallback
                    players = fallback.get("data", [])
                    for p in players:
                        if player_name.lower() in p.get("name", "").lower() and p.get("country", "").lower() in major_nations:
                            best = p
                            break

            if not best:
                return {"error": f"No player found for '{player_name}'"}

            player_id = best["id"]
            player_name_official = best["name"]
            _PLAYER_ID_CACHE[cache_key] = player_id

        # Step 2: fetch full player info
        info_result = self._get("players_info", params={"id": player_id})
        if "error" in info_result:
            return {"error": info_result["error"]}

        data = info_result.get("data", {})
        stats = data.get("stats", [])
        if not player_name_official:
            player_name_official = data.get("name", player_name.title())

        logger.debug("=" * 60)
        logger.debug(f"PLAYER: {player_name_official}")
        logger.debug(f"ROLE: {data.get('role')}")
        logger.debug(f"COUNTRY: {data.get('country')}")
        logger.debug(f"TOTAL STATS: {len(stats)}")

        for s in stats[:20]:
            logger.debug(s)

        logger.debug("=" * 60)

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

        res = {
            "name": player_name_official,
            "country": data.get("country"),
            "role": data.get("role"),
            "dob": data.get("dateOfBirth", "")[:10],
            "batting_stats": batting_parsed,
            "bowling_stats": bowling_parsed,
        }
        _PLAYER_CACHE[cache_key] = {
            "timestamp": time.time(),
            "data": res
        }
        return res