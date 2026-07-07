from src.agents.base import BaseAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.tools.cric_api import CricAPI
from src.llm.client import invoke_llm
from src.config import Config


class MatchupAgent(BaseAgent):
    """
    Matchup Agent cross-references a batter against a bowler.
    Uses local H2H data when available, falls back to LLM reasoning
    from real CricAPI stats for any player combination.
    """

    def __init__(self):
        super().__init__(name="MatchupAgent", role="Batter vs Bowler Matchup Intelligence")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)

    def _get_pitch_context(self, venue: str) -> dict:
        return PITCH_CONDITIONS.get(venue.lower(), {
            "pace": "medium", "bounce": "medium",
            "spin": "medium", "swing": "medium",
            "favours": "balanced conditions"
        })

    def _score_matchup(self, batter_name: str, bowler_name: str, venue: str, fmt: str) -> dict:
        batter = PLAYER_STATS.get(batter_name.lower())
        bowler = BOWLER_STATS.get(bowler_name.lower())

        if not batter or not bowler:
            return {"error": f"Missing local data for {batter_name} or {bowler_name}"}

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
            "weakness_overlap": overlap,
        }

    def _llm_matchup(self, batter_name: str, bowler_name: str,
                     venue: str, fmt: str,
                     batter_stats: dict | None,
                     bowler_stats: dict | None) -> str:
        """
        LLM-based matchup analysis when local H2H data isn't available.
        Uses real CricAPI stats to reason about the matchup.
        """
        pitch = self._get_pitch_context(venue)

        batter_info = "No data available"
        if batter_stats:
            bs = batter_stats.get("batting_stats", {})
            fmt_key = fmt.lower().replace("i", "i")
            # normalize format key
            fmt_map = {"test": "test", "odi": "odi", "t20": "t20i", "t20i": "t20i"}
            fk = fmt_map.get(fmt.lower(), "odi")
            bd = {k: v for k, v in bs.get(fk, {}).items() if k.strip() == k}
            batter_info = (
                f"Name: {batter_stats.get('name')} ({batter_stats.get('country')})\n"
                f"Role: {batter_stats.get('role')}\n"
                f"{fmt} — Avg: {bd.get('avg', 'N/A')}, SR: {bd.get('sr', 'N/A')}, "
                f"Runs: {bd.get('runs', 'N/A')}, HS: {bd.get('hs', 'N/A')}, "
                f"100s: {bd.get('100s', 'N/A')}, 50s: {bd.get('50s', 'N/A')}"
            )

        bowler_info = "No data available"
        if bowler_stats:
            bws = bowler_stats.get("bowling_stats", {})
            fmt_map = {"test": "test", "odi": "odi", "t20": "t20i", "t20i": "t20i"}
            fk = fmt_map.get(fmt.lower(), "odi")
            bwd = {k: v for k, v in bws.get(fk, {}).items() if k.strip() == k}
            bowler_info = (
                f"Name: {bowler_stats.get('name')} ({bowler_stats.get('country')})\n"
                f"Role: {bowler_stats.get('role')}\n"
                f"{fmt} — Wickets: {bwd.get('wkts', 'N/A')}, Avg: {bwd.get('avg', 'N/A')}, "
                f"Economy: {bwd.get('econ', 'N/A')}, SR: {bwd.get('sr', 'N/A')}, "
                f"BBI: {bwd.get('bbi', 'N/A')}"
            )

        prompt = f"""
Batter: {batter_name.title()}
{batter_info}

Bowler: {bowler_name.title()}
{bowler_info}

Venue: {venue.title()}
Pitch: pace={pitch.get('pace')}, bounce={pitch.get('bounce')}, swing={pitch.get('swing')}, spin={pitch.get('spin')}, favours={pitch.get('favours')}
Format: {fmt}
"""

        analysis = invoke_llm(
            system_prompt=(
                "You are an expert cricket analyst specializing in batter-bowler matchups. "
                "Given the stats below, analyze this matchup in 4-5 sentences. "
                "Consider: the batter's strengths and weaknesses based on their stats, "
                "the bowler's threat level based on their wickets and economy, "
                "how the pitch conditions favor either player, "
                "and who has the overall edge. "
                "Be specific with numbers. End with a clear verdict: BATTER EDGE, BOWLER EDGE, or EVENLY MATCHED."
            ),
            user_prompt=prompt,
        )

        return f"""
=== MATCHUP ANALYSIS: {batter_name.title()} vs {bowler_name.title()} ({fmt} at {venue.title()}) ===
[Source: LLM reasoning from real CricAPI stats]

{analysis}
"""

    def run(
        self,
        task: str,
        batter_stats: dict | None = None,
        bowler_stats: dict | None = None
    ) -> str:
        task_lower = task.lower()

        # Find batter
        batter_name = None
        for name in PLAYER_STATS.keys():
            parts = name.split()
            if name in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                batter_name = name
                break

        # Find bowler
        bowler_name = None
        for name in BOWLER_STATS.keys():
            parts = name.split()
            if name in task_lower or any(p in task_lower for p in parts if len(p) > 3):
                bowler_name = name
                break

        # Find venue
        venue = "mumbai"
        for v in PITCH_CONDITIONS.keys():
            if v in task_lower:
                venue = v
                break

        # Find format
        fmt = "ODI"
        if "test" in task_lower:
            fmt = "Test"
        elif "t20" in task_lower:
            fmt = "T20I"
        elif "odi" in task_lower:
            fmt = "ODI"

        # Try local H2H matchup first
        if batter_name and bowler_name:
            result = self._score_matchup(batter_name, bowler_name, venue, fmt)
            if "error" not in result:
                pitch = self._get_pitch_context(venue)
                summary = f"""
Batter: {result['batter']} at {result['venue']} ({result['format']})
Pitch: {pitch}
Bowler score: {result['bowler_score']}/10
Batter score: {result['batter_score']}/10
H2H dismissals: {result['h2h_dismissals']} in {result['h2h_innings']} innings
Weakness overlap: {result['weakness_overlap']}
EDGE: {result['edge']}
"""
                llm_analysis = invoke_llm(
                    system_prompt=(
                        "You are a cricket tactics expert. Given the matchup data, "
                        "write a 4-5 sentence analysis. State clearly who has the edge "
                        "and why. Factor in pitch conditions. Be sharp and direct."
                    ),
                    user_prompt=summary,
                )
                return f"""
=== MATCHUP ANALYSIS: {result['batter']} vs {result['bowler']} ({fmt} at {venue.title()}) ===
Bowler Score : {result['bowler_score']}/10
Batter Score : {result['batter_score']}/10
Edge         : {result['edge']}

TACTICAL ANALYSIS:
{llm_analysis}
"""

        # Fall back to LLM matchup with CricAPI data
        # Extract unknown player names from query
        batter_search = batter_name
        bowler_search = bowler_name

        if not batter_search:
            # Extract batter name — words before "against"
            if "against" in task_lower:
                before = task_lower.split("against")[0]
                skip = {"how", "will", "should", "would", "play", "score",
                        "bat", "face", "can", "the", "a", "an", "in", "at"}
                words = [w.strip(".,!?") for w in before.split()
                         if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
                batter_search = " ".join(words[-2:])

        if not bowler_search:
            # Extract bowler name — words after "against"
            if "against" in task_lower:
                after = task_lower.split("against")[-1]
                skip = {"how", "will", "should", "would", "play", "score",
                        "bowl", "the", "a", "an", "in", "at", "lords",
                        "perth", "mumbai", "test", "odi", "t20"}
                words = [w.strip(".,!?") for w in after.split()
                         if w.strip(".,!?") not in skip and len(w.strip(".,!?")) > 2]
                bowler_search = " ".join(words[:2])

        if not batter_search and not bowler_search:
            return "MatchupAgent: Could not identify batter and bowler in the query."

        # Fetch real stats from CricAPI or use pre-fetched
        resolved_batter_stats = None
        if batter_stats is not None:
            if "error" not in batter_stats and batter_stats.get("batting_stats"):
                resolved_batter_stats = batter_stats
                batter_search = batter_stats.get("name", batter_search)
        else:
            if batter_search:
                result = self.cric_api.get_player_stats(batter_search)
                if "error" not in result:
                    resolved_batter_stats = result

        resolved_bowler_stats = None
        if bowler_stats is not None:
            if "error" not in bowler_stats and bowler_stats.get("bowling_stats"):
                resolved_bowler_stats = bowler_stats
                bowler_search = bowler_stats.get("name", bowler_search)
        else:
            if bowler_search:
                result = self.cric_api.get_player_stats(bowler_search)
                if "error" not in result:
                    resolved_bowler_stats = result

        return self._llm_matchup(
            batter_search or "Unknown Batter",
            bowler_search or "Unknown Bowler",
            venue, fmt,
            resolved_batter_stats,
            resolved_bowler_stats
        )