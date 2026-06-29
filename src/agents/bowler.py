from src.agents.base import BaseAgent
from src.tools.cricket_data import BOWLER_STATS, PLAYER_STATS, resolve_bowlers
from src.llm.client import invoke_llm


class BowlerAgent(BaseAgent):
    """
    Bowler Agent analyzes bowling statistics, strengths, weaknesses,
    and head-to-head records against specific batters.
    """

    def __init__(self):
        super().__init__(name="BowlerAgent", role="Bowling Analysis and Matchup Intelligence")

    def _compute_bowling_rating(self, bowler_name: str) -> dict:
        data = BOWLER_STATS.get(bowler_name.lower())
        if not data:
            return {"error": f"No data found for {bowler_name}"}

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

    def get_matchup(self, bowler_name: str, batter_name: str) -> dict:
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

    def _run_single(self, bowler_name: str, task_lower: str) -> str:
        stats = self._compute_bowling_rating(bowler_name)
        if "error" in stats:
            return f"BowlerAgent Error: {stats['error']}"

        h2h_section = ""
        for batter_name in PLAYER_STATS.keys():
            if batter_name in task_lower:
                h2h = self.get_matchup(bowler_name, batter_name)
                if "error" not in h2h:
                    h2h_section = f"""
Head-to-Head vs {h2h['batter']}:
  Innings       : {h2h['innings']}
  Dismissals    : {h2h['dismissals']}
  Runs conceded : {h2h['runs_conceded']}
  Avg conceded  : {h2h['avg_conceded']}
  Dismissal rate: {h2h['dismissal_rate_pct']}%
  Edge          : {h2h['edge']}
"""

        stats_summary = f"""
Bowler: {stats['bowler']} ({stats['country']})
Style: {stats['bowling_style']}
Speciality: {stats['speciality']}
Recent wickets (oldest to newest): {stats['recent_wickets']}
Weighted avg wickets: {stats['weighted_avg_wickets']}
Average economy: {stats['avg_economy']}
Threat Rating: {stats['threat_rating']}/10
Consistency: {stats['consistency']}
Format economies: {stats['format_economy']}
Format avg wickets: {stats['format_avg_wickets']}
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
=== BOWLING ANALYSIS: {stats['bowler']} ({stats['country']}) ===
Threat Rating     : {stats['threat_rating']}/10
Style             : {stats['bowling_style']}
Consistency       : {stats['consistency'].upper()}
Avg Economy       : {stats['avg_economy']}
Format Economies  : {stats['format_economy']}
Strengths         : {', '.join(stats['strengths'])}
Weaknesses        : {', '.join(stats['weaknesses'])}
{h2h_section}
ANALYST VERDICT:
{llm_analysis}
"""

    def run(self, task: str) -> str:
        task_lower = task.lower()
        resolved = resolve_bowlers(task_lower)
        outputs = [self._run_single(bowler_name, task_lower) for bowler_name in resolved]
        return "\n\n".join(outputs)