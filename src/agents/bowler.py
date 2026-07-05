from src.agents.base import BaseAgent
from src.tools.cricket_data import BOWLER_STATS, PLAYER_STATS
from src.tools.cric_api import CricAPI
from src.llm.client import invoke_llm
from src.config import Config


class BowlerAgent(BaseAgent):
    """
    Bowler Agent analyzes bowling statistics for any bowler.
    Uses CricAPI for real data, falls back to local data for known bowlers.
    """

    def __init__(self):
        super().__init__(name="BowlerAgent", role="Bowling Analysis and Matchup Intelligence")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)

    def _get_real_bowling_stats(self, bowler_name: str) -> dict | None:
        """Fetch real bowling stats from CricAPI."""
        if not bowler_name or len(bowler_name.strip()) < 4:
            return None
        result = self.cric_api.get_player_stats(bowler_name)
        if "error" in result:
            return None
        if not result.get("bowling_stats"):
            return None
        return result

    def _clean_stats(self, stats: dict) -> dict:
        """Remove duplicate keys with spaces."""
        return {
            fmt: {k: v for k, v in s.items() if k.strip() == k}
            for fmt, s in stats.items()
        }

    def _compute_bowling_rating(self, bowler_name: str) -> dict:
        """Compute bowling threat rating from local data."""
        data = BOWLER_STATS.get(bowler_name.lower())
        if not data:
            return {"error": f"No local data found for {bowler_name}"}

        matches = data.get("recent_wickets", [])
        if not matches:
            return {"error": "No recent bowling data available"}

        wickets = [m["wickets"] for m in matches]
        economies = [m["economy"] for m in matches]
        n = len(wickets)

        weights = [2 ** i for i in range(n)]
        weighted_wickets = sum(w * wt for w, wt in zip(wickets, weights)) / sum(weights)
        avg_economy = sum(economies) / n

        wicket_score = min((weighted_wickets / 3.0) * 5, 5)
        economy_score = max(5 - (avg_economy - 2.0), 0)
        threat_rating = round(min(wicket_score + economy_score, 10), 1)

        mean_w = sum(wickets) / n
        variance = sum((w - mean_w) ** 2 for w in wickets) / n
        consistency = "consistent" if variance ** 0.5 < 1.0 else "variable"

        return {
            "bowler": bowler_name.title(),
            "country": data["country"],
            "bowling_style": data["bowling_style"],
            "speciality": data["speciality"],
            "recent_wickets": wickets,
            "weighted_avg_wickets": round(weighted_wickets, 2),
            "avg_economy": round(avg_economy, 2),
            "threat_rating": threat_rating,
            "consistency": consistency,
            "format_economy": data["format_economy"],
            "format_avg_wickets": data["format_avg_wickets"],
            "strengths": data["strengths"],
            "weaknesses": data["weaknesses"],
            "head_to_head": data.get("head_to_head", {}),
        }

    def _extract_bowler_name(self, task_lower: str) -> str:
        """Extract bowler name from query."""
        # Skip words — player names and cricket terms
        batter_words = set()
        for player in PLAYER_STATS.keys():
            for part in player.split():
                batter_words.add(part.lower())

        skip_words = {
            "stats", "average", "record", "career", "bowling", "bowler",
            "how", "many", "wickets", "what", "are", "is", "the", "in", "of", "at",
            "give", "me", "tell", "about", "will", "play", "against", "face",
            "lords", "perth", "mumbai", "sydney", "match", "test", "odi", "t20",
            "can", "she", "her", "his", "him", "brisbane", "melbourne", "london",
            "versus", "vs", "today", "tomorrow", "series", "tour",
            "india", "australia", "england", "pakistan", "africa",
            "zealand", "indies", "lanka", "bangladesh", "should", "would",
            "could", "analysis", "threat", "economy", "spell", "over",
        }

        all_skip = skip_words | batter_words

        words = []
        for w in task_lower.split():
            cleaned = w.rstrip(".,!?")
            if cleaned.endswith("'s"):
                cleaned = cleaned[:-2]
            if cleaned and cleaned not in all_skip and len(cleaned) > 3:
                words.append(cleaned)

        # Bowler usually appears after "against" in the query
        if "against" in task_lower:
            after_against = task_lower.split("against")[-1].strip()
            against_words = []
            for w in after_against.split():
                cleaned = w.rstrip(".,!?")
                if cleaned.endswith("'s"):
                    cleaned = cleaned[:-2]
                # Include short words too (like "sam") when extracting bowler name
                if cleaned and cleaned not in all_skip and len(cleaned) > 2:
                    against_words.append(cleaned)
            if against_words:
                return " ".join(against_words[:2])

        return " ".join(words[:2])


    def _analyze_with_real_stats(self, bowler_name: str, real_stats: dict) -> str:
        """Generate analysis from real CricAPI bowling stats."""
        bs = self._clean_stats(real_stats.get("bowling_stats", {}))

        stats_summary = f"""
Bowler: {real_stats['name']} ({real_stats.get('country', 'N/A')})
Role: {real_stats.get('role', 'N/A')}

CAREER BOWLING STATS (real data from CricAPI):
  Test  — Matches: {bs.get('test', {}).get('m', 'N/A')}, Wickets: {bs.get('test', {}).get('wkts', 'N/A')}, Avg: {bs.get('test', {}).get('avg', 'N/A')}, Economy: {bs.get('test', {}).get('econ', 'N/A')}, SR: {bs.get('test', {}).get('sr', 'N/A')}, BBI: {bs.get('test', {}).get('bbi', 'N/A')}, 5W: {bs.get('test', {}).get('5w', 'N/A')}
  ODI   — Matches: {bs.get('odi', {}).get('m', 'N/A')}, Wickets: {bs.get('odi', {}).get('wkts', 'N/A')}, Avg: {bs.get('odi', {}).get('avg', 'N/A')}, Economy: {bs.get('odi', {}).get('econ', 'N/A')}, SR: {bs.get('odi', {}).get('sr', 'N/A')}, BBI: {bs.get('odi', {}).get('bbi', 'N/A')}
  T20I  — Matches: {bs.get('t20i', {}).get('m', 'N/A')}, Wickets: {bs.get('t20i', {}).get('wkts', 'N/A')}, Avg: {bs.get('t20i', {}).get('avg', 'N/A')}, Economy: {bs.get('t20i', {}).get('econ', 'N/A')}, SR: {bs.get('t20i', {}).get('sr', 'N/A')}, BBI: {bs.get('t20i', {}).get('bbi', 'N/A')}
"""

        llm_analysis = invoke_llm(
            system_prompt=(
                "You are a professional cricket bowling analyst. "
                "Given the career bowling statistics, write a sharp 3-4 sentence analysis. "
                "Mention wicket-taking ability across formats, economy rates, and what kind of "
                "threat this bowler poses. Be direct — like a TV expert."
            ),
            user_prompt=stats_summary,
        )

        return f"""
=== BOWLING ANALYSIS: {real_stats['name']} ({real_stats.get('country', 'N/A')}) — source: CricAPI ===
Test  — Wickets: {bs.get('test', {}).get('wkts', 'N/A')}, Avg: {bs.get('test', {}).get('avg', 'N/A')}, Econ: {bs.get('test', {}).get('econ', 'N/A')}, BBI: {bs.get('test', {}).get('bbi', 'N/A')}
ODI   — Wickets: {bs.get('odi', {}).get('wkts', 'N/A')}, Avg: {bs.get('odi', {}).get('avg', 'N/A')}, Econ: {bs.get('odi', {}).get('econ', 'N/A')}, BBI: {bs.get('odi', {}).get('bbi', 'N/A')}
T20I  — Wickets: {bs.get('t20i', {}).get('wkts', 'N/A')}, Avg: {bs.get('t20i', {}).get('avg', 'N/A')}, Econ: {bs.get('t20i', {}).get('econ', 'N/A')}, BBI: {bs.get('t20i', {}).get('bbi', 'N/A')}

ANALYST VERDICT:
{llm_analysis}
"""

    def _run_local(self, bowler_name: str, task_lower: str) -> str:
        """Run analysis using local hardcoded data."""
        stats = self._compute_bowling_rating(bowler_name)
        if "error" in stats:
            return f"BowlerAgent Error: {stats['error']}"

        h2h_section = ""
        for batter_name in PLAYER_STATS.keys():
            if batter_name in task_lower:
                data = BOWLER_STATS.get(bowler_name, {})
                h2h = data.get("head_to_head", {}).get(batter_name)
                if h2h:
                    dismissal_rate = round(h2h["dismissals"] / h2h["innings"] * 100, 1)
                    edge = "BOWLER" if dismissal_rate > 40 else "BATTER" if dismissal_rate < 25 else "EVENLY MATCHED"
                    h2h_section = f"""
Head-to-Head:
  Innings       : {h2h['innings']}
  Dismissals    : {h2h['dismissals']}
  Avg conceded  : {h2h['avg_conceded']}
  Dismissal rate: {dismissal_rate}%
  Edge          : {edge}
"""

        stats_summary = f"""
Bowler: {stats['bowler']} ({stats['country']})
Style: {stats['bowling_style']}
Speciality: {stats['speciality']}
Recent wickets: {stats['recent_wickets']}
Weighted avg wickets: {stats['weighted_avg_wickets']}
Average economy: {stats['avg_economy']}
Threat Rating: {stats['threat_rating']}/10
Consistency: {stats['consistency']}
Strengths: {', '.join(stats['strengths'])}
Weaknesses: {', '.join(stats['weaknesses'])}
{h2h_section}
"""

        llm_analysis = invoke_llm(
            system_prompt=(
                "You are a professional cricket bowling analyst. "
                "Given the bowling statistics, write a sharp 3-4 sentence analysis. "
                "Mention the threat rating, their key weapon, and how dangerous they are "
                "in specific conditions or formats. If H2H data is present, comment on "
                "who has the edge and why. Be direct — like a TV expert."
            ),
            user_prompt=stats_summary,
        )

        return f"""
=== BOWLING ANALYSIS: {stats['bowler']} ({stats['country']}) — source: local data ===
Threat Rating : {stats['threat_rating']}/10
Style         : {stats['bowling_style']}
Consistency   : {stats['consistency'].upper()}
Avg Economy   : {stats['avg_economy']}
Strengths     : {', '.join(stats['strengths'])}
Weaknesses    : {', '.join(stats['weaknesses'])}
{h2h_section}
ANALYST VERDICT:
{llm_analysis}
"""

    def run(self, task: str) -> str:
        task_lower = task.lower()

        # Check local data first
        local_bowler = None
        for bowler in BOWLER_STATS:
            parts = bowler.split()
            if bowler in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                local_bowler = bowler
                break

        if local_bowler:
            # Try CricAPI first for richer stats, fall back to local
            real_stats = self._get_real_bowling_stats(local_bowler)
            if real_stats and real_stats.get("bowling_stats"):
                return self._analyze_with_real_stats(local_bowler, real_stats)
            return self._run_local(local_bowler, task_lower)

        # Unknown bowler — extract name and try CricAPI
        search_term = self._extract_bowler_name(task_lower)
        print(f"[BowlerAgent] Searching CricAPI for: '{search_term}'")
        real_stats = self._get_real_bowling_stats(search_term) if search_term else None

        if real_stats and real_stats.get("bowling_stats"):
            return self._analyze_with_real_stats(search_term, real_stats)

        return f"BowlerAgent: Could not find bowling data for '{search_term}'. Player may not be in CricAPI database."

    def get_matchup(self, bowler_name: str, batter_name: str) -> dict:
        """Return H2H stats from local data."""
        data = BOWLER_STATS.get(bowler_name.lower(), {})
        h2h = data.get("head_to_head", {}).get(batter_name.lower())
        if not h2h:
            return {"error": f"No H2H data for {bowler_name} vs {batter_name}"}

        dismissal_rate = round(h2h["dismissals"] / h2h["innings"] * 100, 1)
        edge = "BOWLER" if dismissal_rate > 40 else "BATTER" if dismissal_rate < 25 else "EVENLY MATCHED"

        return {
            "bowler": bowler_name.title(),
            "batter": batter_name.title(),
            "innings": h2h["innings"],
            "dismissals": h2h["dismissals"],
            "runs_conceded": h2h["runs_conceded"],
            "avg_conceded": h2h["avg_conceded"],
            "dismissal_rate_pct": dismissal_rate,
            "edge": edge,
        }

    def resolve_bowlers(self, task_lower: str) -> list[str]:
        """Return list of bowler names found in task."""
        found = []
        for bowler in BOWLER_STATS:
            parts = bowler.split()
            if bowler in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                found.append(bowler)
        return found if found else [list(BOWLER_STATS.keys())[0]]