import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import ollama

from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.tools.weather_api import WeatherAPI
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


class MatchupFactor(ABC):
    """
    Abstract base class for a factor in the matchup prediction pipeline.
    """
    @abstractmethod
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        """
        Calculate score and confidence weight contribution for a matchup.

        Parameters:
        - context: dict containing batsman, bowler, venue, format, weather, etc.

        Returns:
        - A tuple of (score, data_points_count, key_factor_description)
          where:
            - score is between 0.0 (favors bowler) and 1.0 (favors batsman)
            - data_points_count is a float representing the quantity/quality of data used (0.0 to 3.0)
            - key_factor_description is a string explaining this score component
        """
        pass


class HeadToHeadFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        batter = context["batsman"]
        bowler = context["bowler"]

        bowler_data = BOWLER_STATS.get(bowler, {})
        h2h = bowler_data.get("head_to_head", {}).get(batter, {})

        if not h2h or h2h.get("innings", 0) == 0:
            return 0.5, 0.0, f"No historical head-to-head data available between {batter.title()} and {bowler.title()}."

        innings = h2h.get("innings", 0)
        dismissals = h2h.get("dismissals", 0)
        runs = h2h.get("runs_conceded", 0)
        avg = h2h.get("avg_conceded", 0)

        # 1. Average-based score (average of 45+ is excellent for batter, <= 20 is excellent for bowler)
        avg_score = min(max((avg - 15) / 35.0, 0.0), 1.0)

        # 2. Dismissal-rate-based score (dismissal every 1-2 innings is high threat, every 5+ innings is low threat)
        dismissal_rate = dismissals / innings
        dismissal_score = 1.0 - min(max((dismissal_rate - 0.1) / 0.4, 0.0), 1.0)

        # Weighted combination of average and dismissal rate
        score = 0.5 * avg_score + 0.5 * dismissal_score

        # Data points score (confidence contribution) - 5+ innings is full data, 1-4 is partial
        data_points = min(innings * 0.6, 3.0)

        desc = (
            f"Historical H2H: {batter.title()} averages {avg:.1f} against {bowler.title()} "
            f"over {innings} innings with {dismissals} dismissals."
        )
        return score, data_points, desc


class BatterRecentFormFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        batter = context["batsman"]
        fmt = context["format"]

        batter_data = PLAYER_STATS.get(batter, {})
        matches = batter_data.get("recent_matches", [])

        if not matches:
            return 0.5, 0.0, f"No recent match data available for {batter.title()}."

        # Filter by format if possible, otherwise use all
        format_matches = [m for m in matches if m["format"] == fmt]
        use_matches = format_matches if len(format_matches) >= 2 else matches

        runs = [m["runs"] for m in use_matches]
        n = len(runs)

        # Exponential decay weights for recent form (latest match is weighted higher)
        weights = [1.5 ** i for i in range(n)]
        weighted_runs = sum(r * w for r, w in zip(runs, weights))
        total_weight = sum(weights)
        weighted_avg = weighted_runs / total_weight

        # Score mapping: weighted average of 60+ is elite, <= 20 is poor
        score = min(max((weighted_avg - 20) / 40.0, 0.0), 1.0)

        # Confidence score (up to 2.0 points)
        data_points = min(n * 0.4, 2.0)

        desc = (
            f"Recent Form ({batter.title()}): Weighted average of {weighted_avg:.1f} "
            f"across {n} recent {fmt if use_matches == format_matches else 'all-format'} matches."
        )
        return score, data_points, desc


class BowlerRecentFormFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        bowler = context["bowler"]
        fmt = context["format"]

        bowler_data = BOWLER_STATS.get(bowler, {})
        spells = bowler_data.get("recent_wickets", [])

        if not spells:
            return 0.5, 0.0, f"No recent match data available for {bowler.title()}."

        format_spells = [s for s in spells if s["format"] == fmt]
        use_spells = format_spells if len(format_spells) >= 2 else spells

        wickets = [s["wickets"] for s in use_spells]
        economies = [s["economy"] for s in use_spells if s.get("economy") is not None]

        avg_wickets = sum(wickets) / len(wickets)
        avg_econ = sum(economies) / len(economies) if economies else (4.0 if fmt == "Test" else 6.0 if fmt == "ODI" else 8.0)

        # Evaluate bowler form strength (0.0 is weak, 1.0 is dominant)
        # Wickets: 2+ per match is elite
        wickets_score = min(avg_wickets / 2.0, 1.0)

        # Economy score
        if fmt == "Test":
            econ_score = 1.0 - min(max((avg_econ - 2.0) / 2.0, 0.0), 1.0)  # <2.0 is elite, >4.0 is expensive
        elif fmt == "ODI":
            econ_score = 1.0 - min(max((avg_econ - 4.0) / 2.5, 0.0), 1.0)  # <4.0 is elite, >6.5 is expensive
        else:  # T20
            econ_score = 1.0 - min(max((avg_econ - 6.5) / 3.0, 0.0), 1.0)  # <6.5 is elite, >9.5 is expensive

        bowler_strength = 0.6 * wickets_score + 0.4 * econ_score

        # Batter success is inverse of bowler strength
        score = 1.0 - bowler_strength

        # Confidence score (up to 2.0 points)
        data_points = min(len(use_spells) * 0.4, 2.0)

        desc = (
            f"Recent Form ({bowler.title()}): Averaging {avg_wickets:.1f} wickets and "
            f"{avg_econ:.1f} economy in recent spells."
        )
        return score, data_points, desc


class VenueConditionsFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        venue = context["venue"]
        bowler = context["bowler"]

        pitch = PITCH_CONDITIONS.get(venue.lower())
        if not pitch:
            return 0.5, 0.0, f"No venue condition data available for {venue.title()}."

        bowler_style = BOWLER_STATS.get(bowler, {}).get("bowling_style", "").lower()
        favours = pitch.get("favours", "").lower()

        # Base neutral score
        score = 0.5

        # Evaluate how pitch interacts with bowler style
        if "pace" in bowler_style or "fast" in bowler_style:
            if pitch.get("pace") == "high" or pitch.get("bounce") == "high":
                score -= 0.15
            if pitch.get("swing") == "high":
                score -= 0.1
        elif "spin" in bowler_style:
            if pitch.get("spin") == "high":
                score -= 0.15

        # Favours check
        if "batter" in favours:
            score += 0.15
        elif "spinners" in favours and "spin" in bowler_style:
            score -= 0.1
        elif "pace" in favours and ("pace" in bowler_style or "fast" in bowler_style):
            score -= 0.1

        score = min(max(score, 0.0), 1.0)

        desc = (
            f"Venue ({venue.title()}): Pitch has {pitch.get('pace')} pace and {pitch.get('bounce')} bounce, "
            f"favouring {pitch.get('favours')}."
        )
        return score, 1.5, desc


class WeatherConditionsFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        weather = context["weather"]
        bowler = context["bowler"]

        if "error" in weather or not weather:
            return 0.5, 0.5, "Weather data unavailable; using neutral weather assumptions."

        bowler_style = BOWLER_STATS.get(bowler, {}).get("bowling_style", "").lower()
        humidity = weather.get("humidity_pct", 50)
        wind = weather.get("wind_speed_mps", 0)
        condition = weather.get("condition", "").lower()

        score = 0.5

        # High humidity and wind help swing/seam bowlers
        if "swing" in bowler_style or "fast" in bowler_style or "pace" in bowler_style:
            if humidity > 70:
                score -= 0.1
            if wind > 5:
                score -= 0.05
            if any(c in condition for c in ["cloud", "overcast", "rain"]):
                score -= 0.05

        score = min(max(score, 0.0), 1.0)

        # Confidence score
        data_points = 1.5 if "error" not in weather else 0.5

        desc = (
            f"Weather: {weather.get('temperature_c')}°C, Humidity {humidity}%, "
            f"Wind {wind} m/s, Condition: {weather.get('condition')}."
        )
        return score, data_points, desc


class StrengthWeaknessMatchupFactor(MatchupFactor):
    def calculate(self, context: dict) -> Tuple[float, float, str]:
        batter = context["batsman"]
        bowler = context["bowler"]

        batter_data = PLAYER_STATS.get(batter, {})
        bowler_data = BOWLER_STATS.get(bowler, {})

        b_weak = batter_data.get("weaknesses", [])
        b_strong = batter_data.get("strengths", [])
        bo_weak = bowler_data.get("weaknesses", [])
        bo_strong = bowler_data.get("strengths", [])

        score = 0.5

        # Bowler strengths overlapping with batter weaknesses (favors bowler, subtract)
        bw_matches = 0
        for w in b_weak:
            for s in bo_strong:
                s_words = [word.strip(",. ") for word in s.split() if len(word) > 2]
                if any(word in w.lower() for word in s_words):
                    score -= 0.15
                    bw_matches += 1
                    break

        # Batter strengths overlapping with bowler weaknesses (favors batter, add)
        bs_matches = 0
        for s in b_strong:
            for w in bo_weak:
                w_words = [word.strip(",. ") for word in w.split() if len(word) > 2]
                if any(word in s.lower() for word in w_words):
                    score += 0.15
                    bs_matches += 1
                    break

        score = min(max(score, 0.0), 1.0)

        desc = (
            f"Tactical Attributes: Found {bw_matches} bowler strength vs batter weakness overlap(s) "
            f"and {bs_matches} batter strength vs bowler weakness overlap(s)."
        )
        return score, 1.5, desc


class MatchupPredictorAgent(BaseAgent):
    """
    Player Matchup Predictor predicts how likely a batsman is to succeed against
    a specific bowler using a weighted multi-factor calculation.
    """
    def __init__(self):
        super().__init__(name="MatchupPredictorAgent", role="Data-Driven Matchup Prediction and Analytics")
        self.config = Config()
        self.weather_api = WeatherAPI(self.config.WEATHER_API_KEY, self.config.WEATHER_API_URL)

        # The prediction pipeline containing modular factors and weights
        self.pipeline: Dict[str, Tuple[MatchupFactor, float]] = {
            "head_to_head": (HeadToHeadFactor(), 0.30),
            "batter_form": (BatterRecentFormFactor(), 0.20),
            "bowler_form": (BowlerRecentFormFactor(), 0.20),
            "venue": (VenueConditionsFactor(), 0.10),
            "weather": (WeatherConditionsFactor(), 0.10),
            "strengths_weaknesses": (StrengthWeaknessMatchupFactor(), 0.10),
        }

    def _get_weather_fallback(self, venue: str) -> dict:
        v = venue.lower()
        if "perth" in v:
            return {"temperature_c": 22.0, "feels_like_c": 21.0, "humidity_pct": 45, "wind_speed_mps": 4.5, "condition": "Clear", "description": "sunny"}
        elif any(name in v for name in ["london", "lord's", "edgbaston", "birmingham"]):
            return {"temperature_c": 16.0, "feels_like_c": 15.0, "humidity_pct": 72, "wind_speed_mps": 5.8, "condition": "Clouds", "description": "overcast"}
        elif any(name in v for name in ["mumbai", "delhi"]):
            return {"temperature_c": 31.0, "feels_like_c": 36.0, "humidity_pct": 82, "wind_speed_mps": 2.5, "condition": "Haze", "description": "humid and hazy"}
        else:  # Sydney / Melbourne / default
            return {"temperature_c": 19.0, "feels_like_c": 18.5, "humidity_pct": 58, "wind_speed_mps": 3.8, "condition": "Clear", "description": "partly cloudy"}

    def run(self, task: str) -> str:
        task_lower = task.lower()

        # Parse batsman
        batsman = None
        for name in PLAYER_STATS.keys():
            if name in task_lower:
                batsman = name
                break
        if not batsman:
            # Fallback check for single word match
            for name in PLAYER_STATS.keys():
                parts = name.split()
                if any(p in task_lower for p in parts if len(p) > 2):
                    batsman = name
                    break

        # Parse bowler
        bowler = None
        for name in BOWLER_STATS.keys():
            if name in task_lower:
                bowler = name
                break
        if not bowler:
            # Fallback check for single word match
            for name in BOWLER_STATS.keys():
                parts = name.split()
                if any(p in task_lower for p in parts if len(p) > 2):
                    bowler = name
                    break

        if not batsman or not bowler:
            return (
                "MatchupPredictorAgent Error: Could not resolve batsman and bowler from the task. "
                "Make sure both names are provided."
            )

        # Parse venue
        venue = "mumbai"  # default
        for v in PITCH_CONDITIONS.keys():
            if v in task_lower:
                venue = v
                break

        # Parse format
        fmt = "ODI"  # default
        if "test" in task_lower:
            fmt = "Test"
        elif "t20" in task_lower:
            fmt = "T20"
        elif "odi" in task_lower:
            fmt = "ODI"

        # Fetch weather conditions
        city = VENUE_TO_CITY.get(venue, venue)
        weather = self.weather_api.get_weather(city)
        if "error" in weather or not weather:
            weather = self._get_weather_fallback(venue)

        # Construct calculation context
        context = {
            "batsman": batsman,
            "bowler": bowler,
            "venue": venue,
            "format": fmt,
            "weather": weather,
        }

        # Run pipeline
        total_score = 0.0
        total_weight = 0.0
        data_points_sum = 0.0
        key_factors = []

        for factor_name, (factor, weight) in self.pipeline.items():
            score, data_points, desc = factor.calculate(context)
            total_score += score * weight
            total_weight += weight
            data_points_sum += data_points
            key_factors.append(desc)

        # Normalize score
        final_score = total_score / total_weight if total_weight > 0 else 0.5

        # Normalize probabilities
        batting_dominance_probability = int(round(final_score * 100))
        dismissal_probability = 100 - batting_dominance_probability

        # Calculate expected runs
        batter_data = PLAYER_STATS.get(batsman, {})
        runs_list = [m["runs"] for m in batter_data.get("recent_matches", [])]
        avg_runs = sum(runs_list) / len(runs_list) if runs_list else 45.0
        expected_runs = int(round(avg_runs * (1.0 + (final_score - 0.5) * 0.8)))
        expected_runs = max(expected_runs, 1)

        # Calculate expected strike rate
        base_sr = 130.0 if fmt == "T20" else 85.0 if fmt == "ODI" else 50.0
        expected_strike_rate = int(round(base_sr * (1.0 + (final_score - 0.5) * 0.4)))

        # Determine confidence level
        if data_points_sum >= 8.0:
            confidence = "High"
        elif data_points_sum >= 4.5:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Ask LLM to generate the final verdict
        prompt = f"""
You are a senior cricket analyst.
Given the calculated matchup prediction metrics below, write a sharp 2-3 sentence explanation (verdict) of this matchup.
Do not use bullet points or any other formatting. Output ONLY the verdict sentences.

Matchup Context:
- Batsman: {batsman.title()}
- Bowler: {bowler.title()}
- Venue: {venue.title()}
- Format: {fmt}
- Dismissal Probability: {dismissal_probability}%
- Batting Dominance Probability: {batting_dominance_probability}%
- Expected Runs: {expected_runs}
- Expected Strike Rate: {expected_strike_rate}
- Confidence: {confidence}
- Key Factors:
  {chr(10).join('- ' + f for f in key_factors)}
"""

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a direct, professional cricket analytics expert."},
                {"role": "user", "content": prompt}
            ]
        )
        verdict = response["message"]["content"].strip()

        output_dict = {
            "batsman": batsman.title(),
            "bowler": bowler.title(),
            "dismissal_probability": dismissal_probability,
            "batting_dominance_probability": batting_dominance_probability,
            "expected_runs": expected_runs,
            "expected_strike_rate": expected_strike_rate,
            "confidence": confidence,
            "key_factors": key_factors,
            "verdict": verdict,
        }

        # Generate visual progress bars
        def make_bar(pct: int, length: int = 20) -> str:
            filled_len = int(round(length * pct / 100))
            bar = "█" * filled_len + "░" * (length - filled_len)
            return f"[{bar}] {pct}%"

        dom_bar = make_bar(batting_dominance_probability)
        dism_bar = make_bar(dismissal_probability)

        return f"""=== PLAYER MATCHUP PREDICTOR ===
Batting Dominance Probability : {dom_bar}
Dismissal Probability         : {dism_bar}

```json
{json.dumps(output_dict, indent=2)}
```"""
