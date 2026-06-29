from src.llm.client import invoke_llm
from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS
from src.config import Config


class CricketAgent(BaseAgent):
    """
    Cricket Agent retrieves, formats, and analyzes cricket match details,
    player statistics, and live match scores.
    """

    def __init__(self):
        super().__init__(name="CricketAgent", role="Cricket Statistics and Analysis")
        self.config = Config()

    def _compute_momentum_score(self, player_name: str) -> dict:
        """
        Compute a weighted momentum score from recent innings.
        Recent innings are weighted more heavily (exponential decay).
        Returns a dict with score, trend, and stats.
        """
        data = PLAYER_STATS.get(player_name.lower())
        if not data:
            return {"error": f"No data found for {player_name}"}

        matches = data.get("recent_matches", [])
        if not matches:
            return {"error": "No recent match data available"}

        runs = [m["runs"] for m in matches]
        formats = [m["format"] for m in matches]
        n = len(runs)

        # Exponential decay weights — most recent innings matters most
        weights = [2 ** i for i in range(n)]  # e.g. [1, 2, 4, 8, 16] for 5 innings
        weighted_sum = sum(r * w for r, w in zip(runs, weights))
        total_weight = sum(weights)
        weighted_avg = weighted_sum / total_weight

        # Format-specific averages
        format_runs = {}
        format_counts = {}
        for r, f in zip(runs, formats):
            format_runs[f] = format_runs.get(f, 0) + r
            format_counts[f] = format_counts.get(f, 0) + 1
        format_avgs = {
            f: round(format_runs[f] / format_counts[f], 1)
            for f in format_runs
        }

        # Trend: compare first half vs second half of innings list
        mid = n // 2
        early_avg = sum(runs[:mid]) / mid if mid > 0 else 0
        recent_avg = sum(runs[mid:]) / (n - mid) if (n - mid) > 0 else 0
        trend = "improving" if recent_avg > early_avg else "declining"

        # Momentum score out of 10 (normalized against a benchmark of 50)
        benchmark = 50
        raw_score = (weighted_avg / benchmark) * 10
        momentum_score = round(min(raw_score, 10), 1)

        # Consistency: standard deviation proxy
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
        """
        Analyze a player's batting form and return a structured report.
        """
        # Extract player name from task (simple keyword search)
        player_name = "virat kohli"  # default
        task_lower = task.lower()
        for name in PLAYER_STATS.keys():
            if name in task_lower:
                player_name = name
                break

        stats = self._compute_momentum_score(player_name)

        if "error" in stats:
            return f"CricketAgent Error: {stats['error']}"

        # Build a structured prompt for Ollama to narrate the stats
        stats_summary = f"""
Player: {stats['player']}
Recent runs (oldest to newest): {stats['recent_runs']}
Formats played: {stats['formats']}
Simple average: {stats['simple_average']}
Weighted average (recent innings count more): {stats['weighted_average']}
Momentum Score: {stats['momentum_score']}/10
Form trend: {stats['trend']}
Consistency: {stats['consistency']}
Format averages: {stats['format_averages']}
Best score: {stats['best']} | Worst score: {stats['worst']}
"""

        llm_analysis = invoke_llm(
            system_prompt=(
                "You are a professional cricket analyst. "
                "Given the following batting statistics, write a sharp 3-4 sentence analysis. "
                "Mention the momentum score, form trend, and one specific insight about format performance. "
                "Be direct and analytical, like a TV expert — no fluff."
            ),
            user_prompt=stats_summary,
        )

        # Return structured output combining numbers + narrative
        return f"""
=== BATTING ANALYSIS: {stats['player']} ===
Momentum Score    : {stats['momentum_score']}/10
Form Trend        : {stats['trend'].upper()}
Consistency       : {stats['consistency'].upper()}
Weighted Average  : {stats['weighted_average']} (simple: {stats['simple_average']})
Format Averages   : {stats['format_averages']}
Recent Scores     : {list(zip(stats['recent_runs'], stats['formats']))}

ANALYST VERDICT:
{llm_analysis}
"""
