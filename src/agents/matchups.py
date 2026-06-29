from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.llm.client import invoke_llm


class MatchupAgent(BaseAgent):
    """
    Matchup Agent cross-references a batter against multiple bowlers,
    factors in pitch conditions, and produces a head-to-head verdict.
    """

    def __init__(self):
        super().__init__(name="MatchupAgent", role="Batter vs Bowler Matchup Intelligence")

    def _get_pitch_context(self, venue: str) -> dict:
        venue_lower = venue.lower()
        return PITCH_CONDITIONS.get(venue_lower, {
            "pace": "medium", "bounce": "medium",
            "spin": "medium", "swing": "medium",
            "favours": "balanced conditions"
        })

    def _score_matchup(self, batter_name: str, bowler_name: str, venue: str, fmt: str) -> dict:
        batter = PLAYER_STATS.get(batter_name.lower())
        bowler = BOWLER_STATS.get(bowler_name.lower())

        if not batter or not bowler:
            return {"error": f"Missing data for {batter_name} or {bowler_name}"}

        pitch = self._get_pitch_context(venue)
        h2h = bowler.get("head_to_head", {}).get(batter_name.lower(), {})

        bowler_score = 0

        if h2h:
            dismissal_rate = h2h["dismissals"] / h2h["innings"]
            bowler_score += dismissal_rate * 4

        pitch_favour = pitch.get("favours", "")
        bowling_style = bowler.get("bowling_style", "")
        if "pace" in bowling_style and "pace" in pitch_favour:
            bowler_score += 2
        if "swing" in bowling_style and "swing" in pitch_favour:
            bowler_score += 2
        if "spin" in bowling_style and "spin" in pitch_favour:
            bowler_score += 2

        batter_weaknesses = batter.get("weaknesses", [])
        bowler_strengths = bowler.get("strengths", [])
        overlap = [w for w in batter_weaknesses
                   if any(s.split()[0] in w for s in bowler_strengths)]
        bowler_score += len(overlap) * 1.5

        bowler_score = round(min(bowler_score, 10), 1)
        batter_score = round(10 - bowler_score, 1)

        if bowler_score > 6:
            edge = f"BOWLER EDGE — {bowler_name.title()}"
        elif batter_score > 6:
            edge = f"BATTER EDGE — {batter_name.title()}"
        else:
            edge = "EVENLY MATCHED"

        return {
            "batter": batter_name.title(),
            "bowler": bowler_name.title(),
            "venue": venue.title(),
            "format": fmt,
            "pitch_favours": pitch.get("favours", "balanced"),
            "bowler_score": bowler_score,
            "batter_score": batter_score,
            "edge": edge,
            "h2h_dismissals": h2h.get("dismissals", "N/A"),
            "h2h_innings": h2h.get("innings", "N/A"),
            "h2h_avg_conceded": h2h.get("avg_conceded", "N/A"),
            "weakness_overlap": overlap,
        }

    def run(self, task: str) -> str:
        task_lower = task.lower()

        batter_name = None
        for name in PLAYER_STATS.keys():
            if name in task_lower:
                batter_name = name
                break

        bowler_names = [name for name in BOWLER_STATS.keys() if name in task_lower]

        venue = "mumbai"
        for v in PITCH_CONDITIONS.keys():
            if v in task_lower:
                venue = v
                break

        fmt = "ODI"
        for f in ["test", "t20", "odi"]:
            if f in task_lower:
                fmt = f.upper()
                break

        if not batter_name:
            return "MatchupAgent: Could not identify batter in task."
        if not bowler_names:
            bowler_names = list(BOWLER_STATS.keys())

        matchup_results = []
        matchup_text = ""
        for bowler_name in bowler_names:
            result = self._score_matchup(batter_name, bowler_name, venue, fmt)
            if "error" not in result:
                matchup_results.append(result)
                matchup_text += f"""
  {result['bowler']} vs {result['batter']}:
    Bowler score    : {result['bowler_score']}/10
    Batter score    : {result['batter_score']}/10
    H2H dismissals  : {result['h2h_dismissals']} in {result['h2h_innings']} innings
    H2H avg conceded: {result['h2h_avg_conceded']}
    Weakness overlap: {result['weakness_overlap'] if result['weakness_overlap'] else 'None identified'}
    EDGE            : {result['edge']}
"""

        pitch = self._get_pitch_context(venue)
        summary = f"""
Batter: {batter_name.title()}
Venue: {venue.title()} — Pitch favours: {pitch['favours']}
Format: {fmt}
Bowlers analysed: {', '.join(b.title() for b in bowler_names)}

MATCHUP BREAKDOWN:
{matchup_text}
"""

        llm_analysis = invoke_llm(
            system_prompt=(
                "You are a cricket tactics expert specializing in batter-bowler matchups. "
                "Given the matchup data, write a 4-5 sentence analysis. "
                "For each bowler, state clearly who has the edge and why. "
                "Factor in the pitch conditions. End with a tactical recommendation "
                "— which bowler should be used first against this batter and why. "
                "Be sharp, direct, and specific."
            ),
            user_prompt=summary,
        )

        matchup_results.sort(key=lambda x: x["bowler_score"], reverse=True)
        verdicts = "\n".join(
            f"  {r['bowler']:20s} → {r['edge']} (bowler score: {r['bowler_score']}/10)"
            for r in matchup_results
        )

        return f"""
=== MATCHUP ANALYSIS: {batter_name.title()} at {venue.title()} ({fmt}) ===
Pitch Profile     : {pitch}

VERDICTS (ranked by bowler threat):
{verdicts}

TACTICAL ANALYSIS:
{llm_analysis}
"""