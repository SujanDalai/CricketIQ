import json
from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.tools.cric_api import CricAPI
from src.tools.weather_api import WeatherAPI
from src.llm.client import invoke_llm
from src.config import Config
from src.logger import logger

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
    and a weighted statistical model, explained by an LLM.
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
        """Extract batter and bowler names from query using local DB and splitters."""
        batter = None
        bowler = None

        # Try to find both using local data
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

        # If both are resolved, return them
        if batter and bowler:
            return batter, bowler

        # Otherwise, try splitting the task
        splitters = ["against", " vs. ", " vs ", " versus ", " v/s ", " v ", " play ", " handle ", " face "]
        splitter = None
        for s in splitters:
            if s in task_lower:
                splitter = s
                break

        if splitter:
            parts_split = task_lower.split(splitter)
            before = parts_split[0]
            after = parts_split[-1]

            skip = {"how", "will", "should", "would", "play", "score", "bat", "face", "can", "the", "a", "an", "in", "at", "handle", "against", "versus", "lords", "perth", "mumbai", "test", "odi", "t20", "brisbane"}
            
            before_words = [w.strip(".,!?") for w in before.split() if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
            after_words = [w.strip(".,!?") for w in after.split() if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
            
            candidate_before = " ".join(before_words[-2:]) if before_words else ""
            candidate_after = " ".join(after_words[:2]) if after_words else ""

            # Check if candidates match local db to assign roles correctly
            found_before_batter = None
            found_before_bowler = None
            found_after_batter = None
            found_after_bowler = None

            if candidate_before:
                for name in PLAYER_STATS.keys():
                    if candidate_before in name or any(p in candidate_before for p in name.split() if len(p) > 3):
                        found_before_batter = name
                        break
                for name in BOWLER_STATS.keys():
                    if candidate_before in name or any(p in candidate_before for p in name.split() if len(p) > 3):
                        found_before_bowler = name
                        break

            if candidate_after:
                for name in PLAYER_STATS.keys():
                    if candidate_after in name or any(p in candidate_after for p in name.split() if len(p) > 3):
                        found_after_batter = name
                        break
                for name in BOWLER_STATS.keys():
                    if candidate_after in name or any(p in candidate_after for p in name.split() if len(p) > 3):
                        found_after_bowler = name
                        break

            # Assign roles based on matches
            if found_before_batter and found_after_bowler:
                batter = found_before_batter
                bowler = found_after_bowler
            elif found_before_bowler and found_after_batter:
                bowler = found_before_bowler
                batter = found_after_batter
            elif found_before_batter:
                batter = found_before_batter
                if not bowler:
                    bowler = candidate_after or found_after_bowler
            elif found_after_bowler:
                bowler = found_after_bowler
                if not batter:
                    batter = candidate_before or found_before_batter
            elif found_before_bowler:
                bowler = found_before_bowler
                if not batter:
                    batter = candidate_after or found_after_batter
            elif found_after_batter:
                batter = found_after_batter
                if not bowler:
                    bowler = candidate_before or found_before_bowler
            else:
                # Direct fallback assuming before is batter, after is bowler
                if not batter:
                    batter = candidate_before
                if not bowler:
                    bowler = candidate_after

        return batter or "", bowler or ""

    def extract_features(
        self,
        batter_name: str,
        bowler_name: str,
        batter_stats: dict | None,
        bowler_stats: dict | None,
        venue: str,
        fmt: str,
        pitch: dict,
        weather: dict,
        use_venue: bool,
        use_weather: bool,
    ) -> dict:
        """
        Phase 1: Feature Extraction.
        Extract statistical, environmental, and recent form features from raw inputs.
        """
        fmt_map = {"test": "test", "odi": "odi", "t20i": "t20i", "overall career": "overall"}
        fmt_key = fmt_map.get(fmt.lower(), "overall")

        # 1. Batter Career stats
        batter_avg = 35.0
        batter_sr = 80.0
        batter_100s = 0
        batter_50s = 0
        batter_matches = 0
        has_real_batter_stats = False

        if batter_stats and "error" not in batter_stats:
            bs = self._clean_stats(batter_stats.get("batting_stats", {}))
            if fmt_key == "overall":
                avgs = []
                srs = []
                for f in ["test", "odi", "t20i"]:
                    fd = bs.get(f, {})
                    if "avg" in fd:
                        try: avgs.append(float(fd["avg"]))
                        except (ValueError, TypeError): pass
                    if "sr" in fd:
                        try: srs.append(float(fd["sr"]))
                        except (ValueError, TypeError): pass
                    try: batter_100s += int(float(fd.get("100s", 0)))
                    except (ValueError, TypeError): pass
                    try: batter_50s += int(float(fd.get("50s", 0)))
                    except (ValueError, TypeError): pass
                    try: batter_matches += int(float(fd.get("m", 0)))
                    except (ValueError, TypeError): pass
                if avgs:
                    batter_avg = sum(avgs) / len(avgs)
                if srs:
                    batter_sr = sum(srs) / len(srs)
            else:
                bd = bs.get(fmt_key, {})
                try: batter_avg = float(bd.get("avg", "35"))
                except (ValueError, TypeError): pass
                try: batter_sr = float(bd.get("sr", "80"))
                except (ValueError, TypeError): pass
                try: batter_100s = int(float(bd.get("100s", 0)))
                except (ValueError, TypeError): pass
                try: batter_50s = int(float(bd.get("50s", 0)))
                except (ValueError, TypeError): pass
                try: batter_matches = int(float(bd.get("m", 0)))
                except (ValueError, TypeError): pass
            
            if batter_stats.get("batting_stats"):
                has_real_batter_stats = True

        # 2. Bowler Career stats
        bowler_avg = 27.0
        bowler_econ = 5.5
        bowler_sr = 40.0
        bowler_wkts = 0
        has_real_bowler_stats = False

        if bowler_stats and "error" not in bowler_stats:
            bws = self._clean_stats(bowler_stats.get("bowling_stats", {}))
            if fmt_key == "overall":
                avgs = []
                econs = []
                srs = []
                for f in ["test", "odi", "t20i"]:
                    fd = bws.get(f, {})
                    if "avg" in fd:
                        try: avgs.append(float(fd["avg"]))
                        except (ValueError, TypeError): pass
                    if "econ" in fd:
                        try: econs.append(float(fd["econ"]))
                        except (ValueError, TypeError): pass
                    if "sr" in fd:
                        try: srs.append(float(fd["sr"]))
                        except (ValueError, TypeError): pass
                    try: bowler_wkts += int(float(fd.get("wkts", 0)))
                    except (ValueError, TypeError): pass
                if avgs:
                    bowler_avg = sum(avgs) / len(avgs)
                if econs:
                    bowler_econ = sum(econs) / len(econs)
                if srs:
                    bowler_sr = sum(srs) / len(srs)
            else:
                bwd = bws.get(fmt_key, {})
                try: bowler_avg = float(bwd.get("avg", "27"))
                except (ValueError, TypeError): pass
                try: bowler_econ = float(bwd.get("econ", "5.5"))
                except (ValueError, TypeError): pass
                try: bowler_sr = float(bwd.get("sr", "40"))
                except (ValueError, TypeError): pass
                try: bowler_wkts = int(float(bwd.get("wkts", 0)))
                except (ValueError, TypeError): pass
            
            if bowler_stats.get("bowling_stats"):
                has_real_bowler_stats = True

        # 3. Environment details (Only use if use_venue / use_weather is True)
        if use_venue:
            pitch_favours = pitch.get("favours", "balanced")
            pitch_pace = pitch.get("pace", "medium")
            pitch_bounce = pitch.get("bounce", "medium")
            pitch_spin = pitch.get("spin", "medium")
            pitch_swing = pitch.get("swing", "medium")
        else:
            pitch_favours = "balanced"
            pitch_pace = "medium"
            pitch_bounce = "medium"
            pitch_spin = "medium"
            pitch_swing = "medium"

        if use_weather and weather:
            try: weather_temp = float(weather.get("temperature_c", "24"))
            except (ValueError, TypeError): pass
            try: weather_humidity = float(weather.get("humidity_pct", "50"))
            except (ValueError, TypeError): pass
            weather_condition = weather.get("condition", "Clear")
        else:
            weather_temp = 24.0
            weather_humidity = 50.0
            weather_condition = "Clear"

        # 4. Recent form extraction
        batter_recent_avg = None
        local_batter = PLAYER_STATS.get(batter_name.lower())
        if local_batter:
            matches = local_batter.get("recent_matches", [])
            fmt_matches = [m["runs"] for m in matches if m.get("format", "").lower() == fmt_key or (fmt_key == "t20i" and m.get("format", "").lower() == "t20")]
            if not fmt_matches:
                fmt_matches = [m["runs"] for m in matches]
            if fmt_matches:
                batter_recent_avg = sum(fmt_matches) / len(fmt_matches)

        bowler_recent_avg_wickets = None
        bowler_recent_econ = None
        local_bowler = BOWLER_STATS.get(bowler_name.lower())
        if local_bowler:
            wickets_list = local_bowler.get("recent_wickets", [])
            fmt_wickets = [w for w in wickets_list if w.get("format", "").lower() == fmt_key or (fmt_key == "t20i" and w.get("format", "").lower() == "t20")]
            if not fmt_wickets:
                fmt_wickets = wickets_list
            if fmt_wickets:
                bowler_recent_avg_wickets = sum(w["wickets"] for w in fmt_wickets) / len(fmt_wickets)
                bowler_recent_econ = sum(w["economy"] for w in fmt_wickets) / len(fmt_wickets)

        # 5. Bowler style
        bowler_role = ""
        if bowler_stats:
            bowler_role = bowler_stats.get("role", "").lower()
        elif local_bowler:
            bowler_role = local_bowler.get("bowling_style", "").lower()
        
        is_spinner = any(kw in bowler_role for kw in ["spin", "orthodox", "legbreak", "offbreak"])
        is_paceman = any(kw in bowler_role for kw in ["pace", "seam", "fast", "medium", "quick"]) or (not is_spinner and bowler_stats)

        return {
            "batter_display_name": batter_stats.get("name", batter_name.title()) if batter_stats else batter_name.title(),
            "bowler_display_name": bowler_stats.get("name", bowler_name.title()) if bowler_stats else bowler_name.title(),
            "batter_avg": batter_avg,
            "batter_sr": batter_sr,
            "batter_100s": batter_100s,
            "batter_50s": batter_50s,
            "batter_matches": batter_matches,
            "bowler_avg": bowler_avg,
            "bowler_econ": bowler_econ,
            "bowler_sr": bowler_sr,
            "bowler_wkts": bowler_wkts,
            "pitch_favours": pitch_favours,
            "pitch_pace": pitch_pace,
            "pitch_bounce": pitch_bounce,
            "pitch_spin": pitch_spin,
            "pitch_swing": pitch_swing,
            "weather_temp": weather_temp,
            "weather_humidity": weather_humidity,
            "weather_condition": weather_condition,
            "batter_recent_avg": batter_recent_avg,
            "bowler_recent_avg_wickets": bowler_recent_avg_wickets,
            "bowler_recent_econ": bowler_recent_econ,
            "is_spinner": is_spinner,
            "is_paceman": is_paceman,
            "has_real_batter_stats": has_real_batter_stats,
            "has_real_bowler_stats": has_real_bowler_stats,
            "is_venue_known": bool(venue and venue.lower() != "unknown"),
            "is_format_known": bool(fmt and fmt.lower() not in ["overall career", "unknown"]),
            "venue": venue,
            "fmt_key": fmt_key,
            "use_venue": use_venue,
            "use_weather": use_weather,
        }

    def calculate_scores(self, features: dict) -> dict:
        """
        Phase 2: Score Calculation.
        Compute capability scores for the batter and the bowler based on extracted features and format bases.
        """
        fmt_key = features["fmt_key"]

        # Base parameters depending on format
        if fmt_key == "t20i":
            sr_base = 130.0
            sr_weight = 0.15
            econ_base = 8.0
            econ_weight = 2.5
            sr_bowler_base = 22.0
            sr_bowler_weight = 0.5
        elif fmt_key == "odi":
            sr_base = 85.0
            sr_weight = 0.2
            econ_base = 5.5
            econ_weight = 4.0
            sr_bowler_base = 35.0
            sr_bowler_weight = 0.3
        elif fmt_key == "test":
            sr_base = 50.0
            sr_weight = 0.1
            econ_base = 3.2
            econ_weight = 6.0
            sr_bowler_base = 60.0
            sr_bowler_weight = 0.15
        else: # overall
            sr_base = 90.0
            sr_weight = 0.15
            econ_base = 5.5
            econ_weight = 4.0
            sr_bowler_base = 40.0
            sr_bowler_weight = 0.3

        # --- Batter capability calculation ---
        batter_score = 50.0
        
        # 1. Career average adjustment (target 35)
        avg_diff = features["batter_avg"] - 35.0
        batter_score += avg_diff * 0.4
        
        # 2. Career strike rate adjustment
        sr_diff = features["batter_sr"] - sr_base
        batter_score += sr_diff * sr_weight
        
        # 3. Hundreds and fifties adjustment (milestones)
        if features.get("batter_matches", 0) > 0:
            ratio = (features["batter_100s"] * 2.0 + features["batter_50s"] * 0.5) / features["batter_matches"]
            milestone_adj = (ratio - 0.15) * 15.0
            batter_score += max(-10.0, min(10.0, milestone_adj))
            
        # 4. Recent form adjustment
        if features["batter_recent_avg"] is not None:
            form_diff = features["batter_recent_avg"] - features["batter_avg"]
            batter_score += form_diff * 0.3
            
        # 5. Pitch adjustment (only if use_venue is True)
        if features.get("use_venue", False):
            if "bat" in features["pitch_favours"].lower():
                batter_score += 3.0
            if features["is_paceman"] and features["pitch_pace"] == "low":
                batter_score += 2.0
            if features["is_spinner"] and features["pitch_spin"] == "low":
                batter_score += 2.0

        # --- Bowler capability calculation ---
        bowler_score = 50.0
        
        # 1. Career average adjustment (target 27)
        bowler_avg_diff = 27.0 - features["bowler_avg"]
        bowler_score += bowler_avg_diff * 0.5
        
        # 2. Career economy adjustment
        econ_diff = econ_base - features["bowler_econ"]
        bowler_score += econ_diff * econ_weight
        
        # 3. Career strike rate adjustment
        sr_bowler_diff = sr_bowler_base - features["bowler_sr"]
        bowler_score += sr_bowler_diff * sr_bowler_weight
        
        # 4. Wickets volume experience adjustment (target base 100 wkts)
        wkt_volume_adj = (features["bowler_wkts"] - 100.0) * 0.02
        bowler_score += max(-5.0, min(5.0, wkt_volume_adj))
        
        # 5. Recent form adjustment (wickets and economy)
        if features["bowler_recent_avg_wickets"] is not None:
            wkt_diff = features["bowler_recent_avg_wickets"] - 1.5
            bowler_score += wkt_diff * 4.0
        if features["bowler_recent_econ"] is not None:
            econ_form_diff = econ_base - features["bowler_recent_econ"]
            bowler_score += econ_form_diff * econ_weight * 0.3
            
        # 6. Pitch adjustment (only if use_venue is True)
        if features.get("use_venue", False):
            if "bowl" in features["pitch_favours"].lower() or "spin" in features["pitch_favours"].lower() or "pace" in features["pitch_favours"].lower():
                bowler_score += 3.0
            if features["is_spinner"] and features["pitch_spin"] == "high":
                bowler_score += 3.0
            elif features["is_paceman"]:
                if features["pitch_pace"] == "high" or features["pitch_bounce"] == "high":
                    bowler_score += 2.5
                if features["pitch_swing"] == "high":
                    bowler_score += 3.0
                    
        # 7. Weather adjustments (only if use_weather is True and helps seamer bowler)
        if features.get("use_weather", False) and features["is_paceman"]:
            if features["weather_humidity"] > 75.0:
                bowler_score += 2.0
            if any(kw in features["weather_condition"].lower() for kw in ["cloud", "rain", "overcast"]):
                bowler_score += 3.0

        return {
            "batter_score": batter_score,
            "bowler_score": bowler_score
        }

    def calculate_probabilities(self, scores: dict, features: dict) -> dict:
        """
        Phase 3: Probability Calculation.
        Compute final head-to-head probabilities, confidence level, and statistical edge from scores.
        """
        diff = scores["batter_score"] - scores["bowler_score"]
        
        # Base batting dominance is 50.0 + diff
        batting_dominance = 50.0 + diff
        
        # Clamp between 20.0 and 80.0
        batting_dominance = max(20.0, min(80.0, batting_dominance))
        batting_prob = int(round(batting_dominance))
        dismissal_prob = 100 - batting_prob

        # Calculate confidence
        has_batter = features["has_real_batter_stats"]
        has_bowler = features["has_real_bowler_stats"]
        is_venue_known = features["is_venue_known"]
        is_format_known = features["is_format_known"]

        if has_batter and has_bowler and is_format_known and is_venue_known:
            confidence = "High"
        elif has_batter and has_bowler and is_format_known:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Determine statistical edge in Python
        if batting_prob > dismissal_prob:
            edge = features["batter_display_name"]
        elif dismissal_prob > batting_prob:
            edge = features["bowler_display_name"]
        else:
            edge = "Evenly Matched"

        return {
            "batting_dominance_probability": batting_prob,
            "dismissal_probability": dismissal_prob,
            "confidence": confidence,
            "edge": edge
        }

    def generate_explanation(self, probs: dict, features: dict, format: str) -> str:
        """
        Phase 4: LLM Explanation.
        Instruct the LLM strictly to explain/justify the pre-calculated outcome.
        """
        batter_recent_info = f", Recent form avg={features['batter_recent_avg']:.1f}" if features['batter_recent_avg'] is not None else ""
        batter_info = (
            f"{features['batter_display_name']} — "
            f"Career Avg={features['batter_avg']:.1f}, SR={features['batter_sr']:.1f}, "
            f"100s={features['batter_100s']}, 50s={features['batter_50s']}, Matches={features['batter_matches']}{batter_recent_info}"
        )

        bowler_recent_info = f", Recent form econ={features['bowler_recent_econ']:.1f}" if features['bowler_recent_econ'] is not None else ""
        bowler_info = (
            f"{features['bowler_display_name']} — "
            f"Career Avg={features['bowler_avg']:.1f}, Econ={features['bowler_econ']:.1f}, SR={features['bowler_sr']:.1f}, "
            f"Wickets={features['bowler_wkts']}{bowler_recent_info}"
        )

        prompt = f"""
BATTER: {batter_info}
BOWLER: {bowler_info}

VENUE: {features['venue'].title() if features['use_venue'] else 'Unknown'}
PITCH: favours={features['pitch_favours']}, pace={features['pitch_pace']}, bounce={features['pitch_bounce']}, spin={features['pitch_spin']}, swing={features['pitch_swing']}
FORMAT: {format}
WEATHER: Temp={features['weather_temp']}°C, Humidity={features['weather_humidity']}%, Condition={features['weather_condition']}

COMPUTED STATISTICS (DO NOT CONTRADICT OR ESTIMATE ANY DIFFERENT NUMBERS):
Batting Dominance Probability: {probs['batting_dominance_probability']}%
Dismissal Chance Probability: {probs['dismissal_probability']}%
Statistical Edge: {probs['edge']}
Confidence Level: {probs['confidence']}
"""

        return invoke_llm(
            system_prompt=(
                "You are a senior cricket analytics expert specializing strictly in player head-to-head matchups.\n"
                "Given the batter and bowler stats, computed probabilities, and statistical edge, provide a sharp matchup explanation in 2-4 sentences.\n"
                "IMPORTANT: You must use the supplied dismissal probability, batting dominance percentages, and statistical edge exactly in your text. Do NOT invent, generate, or estimate any new/different percentages or probabilities. Your role is strictly to explain the analytical reasoning behind these pre-computed numbers based on the player profile, form, pitch, and weather features provided.\n"
                "RULES:\n"
                "1. ONLY discuss: the batter vs bowler matchup, why the statistical edge lies where it does, and the key contributing stats.\n"
                "2. DO NOT predict match scores, runs scored, number of wickets, team totals, or the match winner.\n"
                "3. If venue is Unknown, explain the matchup based purely on the player profiles and stats.\n"
                "4. Be extremely concise (2-4 sentences max). No bullet points."
            ),
            user_prompt=prompt,
        )

    def run(
        self,
        task: str,
        batter_name: str | None = None,
        bowler_name: str | None = None,
        batter_stats: dict | None = None,
        bowler_stats: dict | None = None,
        venue: str | None = None,
        format: str | None = None,
        use_weather: bool = False,
    ) -> str:
        task_lower = task.lower()

        if not batter_name or not bowler_name:
            logger.debug(f"[MatchupPredictor] Batter = {batter_name} | Bowler = {bowler_name}")
            extracted_batter, extracted_bowler = self._extract_names(task_lower)

            if not batter_name:
                batter_name = extracted_batter

            if not bowler_name:
                bowler_name = extracted_bowler

        if not batter_name or not bowler_name:
            return "MatchupPredictorAgent: Could not identify both batter and bowler in query."

        # Find venue and format if not passed
        if not venue or venue.lower() == "unknown":
            resolved_venue = None
            for v in PITCH_CONDITIONS.keys():
                if v in task_lower:
                    resolved_venue = v
                    break
            venue = resolved_venue or "Unknown"

        fmt = format
        if not fmt or fmt.lower() in ["overall career", "unknown"]:
            resolved_fmt = None
            if "test" in task_lower:
                resolved_fmt = "Test"
            elif "t20" in task_lower:
                resolved_fmt = "T20I"
            elif "odi" in task_lower:
                resolved_fmt = "ODI"
            fmt = resolved_fmt or "Overall Career"

        fmt_map = {"test": "test", "odi": "odi", "t20i": "t20i", "overall career": "overall"}
        fmt_key = fmt_map.get(fmt.lower(), "overall")

        use_venue = venue.lower() != "unknown"

        # Get weather and pitch details
        if not use_venue:
            weather = {}
            pitch = {}
        else:
            city = VENUE_TO_CITY.get(venue, venue)
            weather = {}
            if use_weather:
                weather = self.weather_api.get_weather(city)
                if "error" in weather or not weather:
                    weather = self._get_weather_fallback(venue)
            
            pitch = PITCH_CONDITIONS.get(venue.lower(), {
                "pace": "medium", "bounce": "medium",
                "spin": "medium", "swing": "medium",
                "favours": "balanced"
            })

        # Fetch real stats from CricAPI or use pre-fetched
        if batter_stats is not None:
            if "error" not in batter_stats and batter_stats.get("batting_stats"):
                batter_name = batter_stats.get("name", batter_name)
            else:
                batter_stats = None
        else:
            if batter_name:
                batter_result = self.cric_api.get_player_stats(batter_name)
                logger.debug(f"[MatchupPredictor] Batter result resolved from CricAPI")
                if "error" not in batter_result:
                    batter_stats = batter_result
                else:
                    batter_stats = None

        if bowler_stats is not None:
            if "error" not in bowler_stats and bowler_stats.get("bowling_stats"):
                bowler_name = bowler_stats.get("name", bowler_name)
            else:
                bowler_stats = None
        else:
            if bowler_name:
                bowler_result = self.cric_api.get_player_stats(bowler_name)
                logger.debug(f"[MatchupPredictor] Bowler result resolved from CricAPI")
                if "error" not in bowler_result:
                    bowler_stats = bowler_result
                else:
                    bowler_stats = None

        # Build features dictionary using Phase 1
        features = self.extract_features(
            batter_name=batter_name,
            bowler_name=bowler_name,
            batter_stats=batter_stats,
            bowler_stats=bowler_stats,
            venue=venue,
            fmt=fmt,
            pitch=pitch,
            weather=weather,
            use_venue=use_venue,
            use_weather=use_weather
        )

        # Calculate capability scores using Phase 2
        scores = self.calculate_scores(features)

        # Calculate head-to-head probabilities using Phase 3
        probs = self.calculate_probabilities(scores, features)

        # Generate expert LLM explanation using Phase 4
        verdict = self.generate_explanation(probs, features, fmt)

        def make_bar(pct: int, length: int = 12) -> str:
            filled = int(round(length * pct / 100))
            return f"{'█' * filled}{'░' * (length - filled)}"

        batter_display_name = features["batter_display_name"]
        bowler_display_name = features["bowler_display_name"]
        dismissal_prob = probs["dismissal_probability"]
        batting_prob = probs["batting_dominance_probability"]
        confidence = probs["confidence"]

        output_dict = {
            "batsman": batter_display_name,
            "bowler": bowler_display_name,
            "format": fmt,
            "venue": venue.title(),
            "dismissal_probability": dismissal_prob,
            "batting_dominance_probability": batting_prob,
            "confidence": confidence,
            "statistical_edge": probs["edge"],
            "data_source": "CricAPI real statistics + weighted statistical model + LLM explanation",
            "verdict": verdict,
        }

        # Construct key factors strings for presentation
        if features["has_real_batter_stats"]:
            batter_factor = f"Batter strength: {batter_display_name} has a format average of {features['batter_avg']:.2f}."
        else:
            batter_factor = f"Batter strength: {batter_display_name} statistics not available."

        if features["has_real_bowler_stats"]:
            bowler_factor = f"Bowler strength: {bowler_display_name} bowling average of {features['bowler_avg']:.2f} and economy of {features['bowler_econ']:.2f}."
        else:
            bowler_factor = f"Bowler strength: {bowler_display_name} statistics not available."

        if not use_venue:
            pitch_factor = "Pitch: Venue-specific effects were not included because no venue was provided."
            weather_factor = "Weather: Weather-specific effects were not included because no venue was provided."
        else:
            pitch_factor = f"Pitch: pace={features['pitch_pace']}, bounce={features['pitch_bounce']}, swing={features['pitch_swing']}, spin={features['pitch_spin']}, favours={features['pitch_favours']}."
            weather_factor = f"Weather: temp={features['weather_temp']}°C, humidity={features['weather_humidity']}%, condition={features['weather_condition']}."

        if features["batter_recent_avg"] is not None:
            recent_form_factor = f"Recent form: Evaluated using local matches for {batter_display_name} (avg: {features['batter_recent_avg']:.1f})."
        else:
            recent_form_factor = f"Recent form: Evaluated using career baseline statistics for {fmt} matchups."

        return f"""-----------------------------------
PLAYER MATCHUP PREDICTION
-----------------------------------

Batter: {batter_display_name}
Bowler: {bowler_display_name}
Venue: {venue.title()}
Format: {fmt}

Batting Dominance
{make_bar(batting_prob)} {batting_prob}%

Dismissal Chance
{make_bar(dismissal_prob)} {dismissal_prob}%

Confidence
{confidence}

Key Factors
• {batter_factor}
• {bowler_factor}
• {pitch_factor}
• {weather_factor}
• {recent_form_factor}

Expert Verdict
{verdict}

JSON
```json
{json.dumps(output_dict, indent=2)}
```
"""