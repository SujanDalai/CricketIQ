import json
from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.tools.cric_api import CricAPI
from src.tools.weather_api import WeatherAPI
from src.llm.client import invoke_llm
from src.config import Config


VENUE_TO_CITY = {
    "perth": "Perth,AU",
    "mumbai": "Mumbai,IN",
    "lord's": "London,GB",
    "lords": "London,GB",
    "edgbaston": "Birmingham,GB",
    "sydney": "Sydney,AU",
    "melbourne": "Melbourne,AU",
    "delhi": "Delhi,IN",
    "birmingham": "Birmingham,GB",
    "chennai": "Chennai,IN",
    "kolkata": "Kolkata,IN",
    "bangalore": "Bangalore,IN",
    "dubai": "Dubai,AE",
    "auckland": "Auckland,NZ",
    "johannesburg": "Johannesburg,ZA",
}


class MatchupPredictorAgent(BaseAgent):
    """
    Predicts batter vs bowler matchup outcome using real CricAPI stats
    and LLM reasoning. Works for any player combination.
    """

    def __init__(self):
        super().__init__(name="MatchupPredictorAgent", role="Data-Driven Matchup Prediction")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)
        self.weather_api = WeatherAPI(config.WEATHER_API_KEY, config.WEATHER_API_URL)

    def _get_weather_fallback(self, venue: str) -> dict:
        v = venue.lower()
        if "perth" in v:
            return {"temperature_c": 22.0, "humidity_pct": 45, "wind_speed_mps": 4.5, "condition": "Clear"}
        elif any(n in v for n in ["london", "lords", "edgbaston", "birmingham"]):
            return {"temperature_c": 16.0, "humidity_pct": 72, "wind_speed_mps": 5.8, "condition": "Clouds"}
        elif any(n in v for n in ["mumbai", "delhi", "chennai", "kolkata", "bangalore"]):
            return {"temperature_c": 31.0, "humidity_pct": 82, "wind_speed_mps": 2.5, "condition": "Haze"}
        else:
            return {"temperature_c": 24.0, "humidity_pct": 60, "wind_speed_mps": 3.5, "condition": "Clear"}

    def _clean_stats(self, stats: dict) -> dict:
        return {
            fmt: {k: v for k, v in s.items() if k.strip() == k}
            for fmt, s in stats.items()
        }

    def _extract_names(self, task_lower: str) -> tuple[str, str]:
        """Extract batter and bowler names from query."""
        batter = None
        bowler = None

        # Check local data first
        for name in PLAYER_STATS.keys():
            parts = name.split()
            if name in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                batter = name
                break

        for name in BOWLER_STATS.keys():
            parts = name.split()
            if name in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                bowler = name
                break

        # Dynamic extraction if not found locally
        if not batter and "against" in task_lower:
            before = task_lower.split("against")[0]
            skip = {"how", "will", "should", "would", "play", "score",
                    "bat", "face", "can", "the", "a", "an", "in", "at"}
            words = [w.strip(".,!?") for w in before.split()
                     if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
            batter = " ".join(words[-2:]) if words else None

        if not bowler and "against" in task_lower:
            after = task_lower.split("against")[-1]
            skip = {"how", "will", "should", "would", "play", "score",
                    "bowl", "the", "a", "an", "in", "at", "lords",
                    "perth", "mumbai", "test", "odi", "t20", "brisbane"}
            words = [w.strip(".,!?") for w in after.split()
                     if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
            bowler = " ".join(words[:2]) if words else None

        return batter or "", bowler or ""

    def _estimate_probabilities(self, bowler_stats: dict | None, fmt_key: str) -> tuple[int, int]:
        """Estimate dismissal/batting probabilities from bowler stats."""
        dismissal_prob = 50
        if bowler_stats:
            bws = self._clean_stats(bowler_stats.get("bowling_stats", {}))
            bwd = bws.get(fmt_key, {})
            avg = bwd.get("avg", "30")
            try:
                avg_float = float(avg)
                if avg_float < 20:
                    dismissal_prob = 65
                elif avg_float < 28:
                    dismissal_prob = 57
                elif avg_float < 35:
                    dismissal_prob = 50
                else:
                    dismissal_prob = 43
            except (ValueError, TypeError):
                pass
        return dismissal_prob, 100 - dismissal_prob

    def run(self, task: str) -> str:
        task_lower = task.lower()

        # Extract player names
        batter_name, bowler_name = self._extract_names(task_lower)

        if not batter_name or not bowler_name:
            return "MatchupPredictorAgent: Could not identify both batter and bowler in query."

        # Find venue and format
        venue = "mumbai"
        for v in PITCH_CONDITIONS.keys():
            if v in task_lower:
                venue = v
                break

        fmt = "ODI"
        if "test" in task_lower:
            fmt = "Test"
        elif "t20" in task_lower:
            fmt = "T20I"

        fmt_map = {"test": "test", "odi": "odi", "t20i": "t20i"}
        fmt_key = fmt_map.get(fmt.lower(), "odi")

        # Get weather
        city = VENUE_TO_CITY.get(venue, venue)
        weather = self.weather_api.get_weather(city)
        if "error" in weather or not weather:
            weather = self._get_weather_fallback(venue)

        # Fetch real stats from CricAPI
        batter_stats = None
        bowler_stats = None

        batter_result = self.cric_api.get_player_stats(batter_name)
        if "error" not in batter_result:
            batter_stats = batter_result

        bowler_result = self.cric_api.get_player_stats(bowler_name)
        if "error" not in bowler_result:
            bowler_stats = bowler_result

        # Build context for LLM
        pitch = PITCH_CONDITIONS.get(venue.lower(), {
            "pace": "medium", "bounce": "medium",
            "spin": "medium", "swing": "medium",
            "favours": "balanced"
        })

        batter_info = "Stats not available"
        if batter_stats:
            bs = self._clean_stats(batter_stats.get("batting_stats", {}))
            bd = bs.get(fmt_key, {})
            batter_info = (
                f"{batter_stats.get('name')} ({batter_stats.get('country')}) — {batter_stats.get('role')}\n"
                f"{fmt}: Avg={bd.get('avg','N/A')}, SR={bd.get('sr','N/A')}, "
                f"Runs={bd.get('runs','N/A')}, HS={bd.get('hs','N/A')}, "
                f"100s={bd.get('100s','N/A')}, 50s={bd.get('50s','N/A')}"
            )

        bowler_info = "Stats not available"
        if bowler_stats:
            bws = self._clean_stats(bowler_stats.get("bowling_stats", {}))
            bwd = bws.get(fmt_key, {})
            bowler_info = (
                f"{bowler_stats.get('name')} ({bowler_stats.get('country')}) — {bowler_stats.get('role')}\n"
                f"{fmt}: Wkts={bwd.get('wkts','N/A')}, Avg={bwd.get('avg','N/A')}, "
                f"Econ={bwd.get('econ','N/A')}, SR={bwd.get('sr','N/A')}, "
                f"BBI={bwd.get('bbi','N/A')}"
            )

        dismissal_prob, batting_prob = self._estimate_probabilities(bowler_stats, fmt_key)

        prompt = f"""
BATTER: {batter_info}

BOWLER: {bowler_info}

VENUE: {venue.title()}
PITCH: pace={pitch.get('pace')}, bounce={pitch.get('bounce')}, swing={pitch.get('swing')}, spin={pitch.get('spin')}, favours={pitch.get('favours')}
FORMAT: {fmt}
WEATHER: {weather.get('temperature_c')}°C, Humidity={weather.get('humidity_pct')}%, Condition={weather.get('condition')}

Estimated dismissal probability: {dismissal_prob}%
Estimated batting dominance: {batting_prob}%
"""

        verdict = invoke_llm(
            system_prompt=(
                "You are a senior cricket analytics expert. "
                "Given the batter and bowler stats, provide a sharp matchup prediction in 3-4 sentences. "
                "Cover: who has the edge, why, key pitch/weather factors, and a final prediction. "
                "Be specific with the numbers provided. No bullet points."
            ),
            user_prompt=prompt,
        )

        def make_bar(pct: int, length: int = 20) -> str:
            filled = int(round(length * pct / 100))
            return f"[{'█' * filled}{'░' * (length - filled)}] {pct}%"

        output_dict = {
            "batsman": batter_stats.get("name", batter_name.title()) if batter_stats else batter_name.title(),
            "bowler": bowler_stats.get("name", bowler_name.title()) if bowler_stats else bowler_name.title(),
            "format": fmt,
            "venue": venue.title(),
            "dismissal_probability": dismissal_prob,
            "batting_dominance_probability": batting_prob,
            "confidence": "Medium" if (batter_stats and bowler_stats) else "Low",
            "data_source": "CricAPI real stats + LLM reasoning",
            "verdict": verdict,
        }

        return f"""=== PLAYER MATCHUP PREDICTOR ===
Batting Dominance : {make_bar(batting_prob)}
Dismissal Prob    : {make_bar(dismissal_prob)}

```json
{json.dumps(output_dict, indent=2)}
```

FULL ANALYSIS:
{verdict}
"""