import ollama
from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.config import Config


class MatchupAgent(BaseAgent):
    """
    Matchup Agent cross-references a batter against multiple bowlers,
    factors in pitch conditions, and produces a head-to-head verdict.
    """

    def __init__(self):
        super().__init__(name="MatchupAgent", role="Batter vs Bowler Matchup Intelligence")
        self.config = Config()

    def _get_pitch_context(self, venue: str) -> dict:
        venue_lower = venue.lower()
        return PITCH_CONDITIONS.get(venue_lower, {
            "pace": "medium", "bounce": "medium",
            "spin": "medium", "swing": "medium",
            "favours": "balanced conditions"
        })

    def _score_matchup(self, batter_name: str, bowler_name: str, venue: str, fmt: str) -> dict:
        """
        Score a single batter vs bowler matchup at a specific venue and format.
        Returns a verdict with reasoning.
        """
        batter = PLAYER_STATS.get(batter_name.lower())
        bowler = BOWLER_STATS.get(bowler_name.lower())

        if not batter or not bowler:
            return {"error": f"Missing data for {batter_name} or {bowler_name}"}

        pitch = self._get_pitch_context(venue)
        h2h = bowler.get("head_to_head", {}).get(batter_name.lower(), {})

        # Score bowler threat in this matchup (0-10)
        bowler_score = 0

        # H2H dismissal rate
        if h2h:
            dismissal_rate = h2h["dismissals"] / h2h["innings"]
            bowler_score += dismissal_rate * 4  # max ~4 pts

        # Pitch suits bowler?
        pitch_favour = pitch.get("favours", "")
        bowling_style = bowler.get("bowling_style", "")
        if "pace" in bowling_style and "pace" in pitch_favour:
            bowler_score += 2
        if "swing" in bowling_style and "swing" in pitch_favour:
            bowler_score += 2
        if "spin" in bowling_style and "spin" in pitch_favour:
            bowler_score += 2

        # Batter weakness matches bowler strength?
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
        """
        Run matchup analysis. Detects batter, bowlers, venue, and format from task string.
        """
        task_lower = task.lower()

        # Detect batter
        batter_name = None
        for name in PLAYER_STATS.keys():
            if name in task_lower:
                batter_name = name
                break

        # Detect bowlers (can be multiple)
        bowler_names = []
        for name in BOWLER_STATS.keys():
            if name in task_lower:
                bowler_names.append(name)

        # Detect venue
        venue = "mumbai"  # default
        for v in PITCH_CONDITIONS.keys():
            if v in task_lower:
                venue = v
                break

        # Detect format
        fmt = "ODI"
        for f in ["test", "t20", "odi"]:
            if f in task_lower:
                fmt = f.upper()
                break

        if not batter_name:
            return "MatchupAgent: Could not identify batter in task."
        if not bowler_names:
            # Default to all bowlers if none specified
            bowler_names = list(BOWLER_STATS.keys())

        # Score each matchup
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

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cricket tactics expert specializing in batter-bowler matchups. "
                        "Given the matchup data, write a 4-5 sentence analysis. "
                        "For each bowler, state clearly who has the edge and why. "
                        "Factor in the pitch conditions. End with a tactical recommendation "
                        "— which bowler should be used first against this batter and why. "
                        "Be sharp, direct, and specific."
                    ),
                },
                {"role": "user", "content": summary},
            ],
        )

        llm_analysis = response["message"]["content"]

        # Sort matchups: most dangerous bowler first
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
