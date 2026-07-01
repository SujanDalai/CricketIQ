from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS
from src.tools.cric_api import CricAPI
from src.llm.client import invoke_llm
from src.config import Config


class CricketAgent(BaseAgent):
    """
    Cricket Agent retrieves real player stats from CricAPI and analyzes
    batting form. Falls back to local data if API is unavailable.
    """

    def __init__(self):
        super().__init__(name="CricketAgent", role="Cricket Statistics and Analysis")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)

    def _get_real_stats(self, player_name: str) -> dict | None:
        """Fetch real stats from CricAPI. Returns None on failure."""
        result = self.cric_api.get_player_stats(player_name)
        if "error" in result:
            return None
        return result

    def _compute_momentum_score(self, player_name: str) -> dict:
        """
        Compute a weighted momentum score from local recent innings data.
        Used as supplementary context alongside real career stats.
        """
        data = PLAYER_STATS.get(player_name.lower())
        if not data:
            return {"error": f"No local data found for {player_name}"}

        matches = data.get("recent_matches", [])
        if not matches:
            return {"error": "No recent match data available"}

        runs = [m["runs"] for m in matches]
        formats = [m["format"] for m in matches]
        n = len(runs)

        weights = [2 ** i for i in range(n)]
        weighted_sum = sum(r * w for r, w in zip(runs, weights))
        total_weight = sum(weights)
        weighted_avg = weighted_sum / total_weight

        format_runs = {}
        format_counts = {}
        for r, f in zip(runs, formats):
            format_runs[f] = format_runs.get(f, 0) + r
            format_counts[f] = format_counts.get(f, 0) + 1
        format_avgs = {
            f: round(format_runs[f] / format_counts[f], 1)
            for f in format_runs
        }

        mid = n // 2
        early_avg = sum(runs[:mid]) / mid if mid > 0 else 0
        recent_avg = sum(runs[mid:]) / (n - mid) if (n - mid) > 0 else 0
        trend = "improving" if recent_avg > early_avg else "declining"

        benchmark = 50
        raw_score = (weighted_avg / benchmark) * 10
        momentum_score = round(min(raw_score, 10), 1)

        mean = sum(runs) / n
        variance = sum((r - mean) ** 2 for r in runs) / n
        std_dev = variance ** 0.5
        consistency = "consistent" if std_dev < 20 else "inconsistent"

        return {
            "player": player_name.title(),
            "recent_runs": runs,
            "formats": formats,
            "simple_average": round(mean, 1),
            "weighted_average": round(weighted_avg, 1),
            "momentum_score": momentum_score,
            "trend": trend,
            "consistency": consistency,
            "format_averages": format_avgs,
            "best": max(runs),
            "worst": min(runs),
        }

    def run(self, task: str) -> str:
        task_lower = task.lower()

        # Detect player name
        player_name = None
        for name in PLAYER_STATS.keys():
            parts = name.split()
            if name in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                player_name = name
                break

        if not player_name:
            # Try to search CricAPI directly with words from the query
            skip_words = {
                "stats", "average", "record", "career", "ipl", "t20", "odi", "test",
                "how", "many", "runs", "what", "are", "is", "the", "in", "of",
                "score", "batting", "give", "me", "tell", "about", "2025", "2026"
            }
            words = [w for w in task_lower.split() if w not in skip_words and len(w) > 3]
            search_term = " ".join(words[:3])
            if search_term:
                real_stats = self._get_real_stats(search_term)
                if real_stats:
                    llm_analysis = invoke_llm(
                        system_prompt=(
                            "You are a professional cricket analyst. "
                            "Given the following career batting statistics, write a sharp 3-4 sentence analysis. "
                            "Note: IPL stats are not available, only international career stats. "
                            "Be direct and specific with the numbers."
                        ),
                        user_prompt=str(real_stats),
                    )
                    return f"=== BATTING ANALYSIS: {real_stats['name']} ===\n{llm_analysis}"
            return "CricketAgent: Could not find player data. Note: IPL-specific stats are not available on the free tier. "

        # Try real API stats first
        real_stats = self._get_real_stats(player_name)

        # Also get momentum from local data
        momentum = self._compute_momentum_score(player_name)
        momentum_section = ""
        if "error" not in momentum:
            momentum_section = f"""
Recent innings (local data):
  Scores        : {list(zip(momentum['recent_runs'], momentum['formats']))}
  Momentum Score: {momentum['momentum_score']}/10
  Form Trend    : {momentum['trend'].upper()}
  Consistency   : {momentum['consistency'].upper()}
"""

        if real_stats:
            bs = real_stats["batting_stats"]
            # Clean stats — remove keys with spaces
            cleaned = {}
            for fmt, stats in bs.items():
                cleaned[fmt] = {k: v for k, v in stats.items() if k.strip() == k}

            stats_summary = f"""
Player: {real_stats['name']} ({real_stats['country']})
Role: {real_stats['role']}

CAREER BATTING STATS (real data from CricAPI):
  Test  — Matches: {cleaned.get('test', {}).get('m', 'N/A')}, Runs: {cleaned.get('test', {}).get('runs', 'N/A')}, Avg: {cleaned.get('test', {}).get('avg', 'N/A')}, SR: {cleaned.get('test', {}).get('sr', 'N/A')}, 100s: {cleaned.get('test', {}).get('100s', 'N/A')}, 50s: {cleaned.get('test', {}).get('50s', 'N/A')}
  ODI   — Matches: {cleaned.get('odi', {}).get('m', 'N/A')}, Runs: {cleaned.get('odi', {}).get('runs', 'N/A')}, Avg: {cleaned.get('odi', {}).get('avg', 'N/A')}, SR: {cleaned.get('odi', {}).get('sr', 'N/A')}, 100s: {cleaned.get('odi', {}).get('100s', 'N/A')}, 50s: {cleaned.get('odi', {}).get('50s', 'N/A')}
  T20I  — Matches: {cleaned.get('t20i', {}).get('m', 'N/A')}, Runs: {cleaned.get('t20i', {}).get('runs', 'N/A')}, Avg: {cleaned.get('t20i', {}).get('avg', 'N/A')}, SR: {cleaned.get('t20i', {}).get('sr', 'N/A')}, 100s: {cleaned.get('t20i', {}).get('100s', 'N/A')}, 50s: {cleaned.get('t20i', {}).get('50s', 'N/A')}
{momentum_section}
"""
            source = "CricAPI (real data)"
        else:
            # Fallback to local data
            if "error" in momentum:
                return f"CricketAgent Error: {momentum['error']}"
            stats_summary = f"""
Player: {momentum['player']}
Simple average  : {momentum['simple_average']}
Weighted average: {momentum['weighted_average']}
Momentum Score  : {momentum['momentum_score']}/10
Form Trend      : {momentum['trend'].upper()}
Consistency     : {momentum['consistency'].upper()}
Format Averages : {momentum['format_averages']}
Recent Scores   : {list(zip(momentum['recent_runs'], momentum['formats']))}
"""
            source = "local data (CricAPI unavailable)"

        llm_analysis = invoke_llm(
            system_prompt=(
                "You are a professional cricket analyst. "
                "Given the following batting statistics, write a sharp 3-4 sentence analysis. "
                "Mention career averages across formats, current form trend, and one specific insight. "
                "Be direct and analytical, like a TV expert — no fluff."
            ),
            user_prompt=stats_summary,
        )

        header = f"=== BATTING ANALYSIS: {player_name.title()} (source: {source}) ==="

        if real_stats:
            bs_clean = {fmt: {k: v for k, v in stats.items() if k.strip() == k}
                       for fmt, stats in real_stats["batting_stats"].items()}
            return f"""
{header}
Test  — Runs: {bs_clean.get('test', {}).get('runs', 'N/A')}, Avg: {bs_clean.get('test', {}).get('avg', 'N/A')}, 100s: {bs_clean.get('test', {}).get('100s', 'N/A')}
ODI   — Runs: {bs_clean.get('odi', {}).get('runs', 'N/A')}, Avg: {bs_clean.get('odi', {}).get('avg', 'N/A')}, 100s: {bs_clean.get('odi', {}).get('100s', 'N/A')}
T20I  — Runs: {bs_clean.get('t20i', {}).get('runs', 'N/A')}, Avg: {bs_clean.get('t20i', {}).get('avg', 'N/A')}, 100s: {bs_clean.get('t20i', {}).get('100s', 'N/A')}
{momentum_section}
ANALYST VERDICT:
{llm_analysis}
"""
        else:
            return f"""
{header}
Momentum Score : {momentum['momentum_score']}/10
Form Trend     : {momentum['trend'].upper()}
Consistency    : {momentum['consistency'].upper()}
Recent Scores  : {list(zip(momentum['recent_runs'], momentum['formats']))}

ANALYST VERDICT:
{llm_analysis}
"""