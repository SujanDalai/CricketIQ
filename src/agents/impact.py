from src.agents.base import BaseAgent
from src.tools.cric_api import CricAPI
from src.llm.client import invoke_llm
from src.config import Config
from src.logger import logger


class ImpactAgent(BaseAgent):
    """
    Impact Agent analyzes a completed match scorecard and identifies
    the key turning points — which overs/dismissals changed the game.
    """

    def __init__(self):
        super().__init__(name="ImpactAgent", role="Match Turning Point Analysis")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)

    def _search_match(self, query: str) -> tuple[str | None, str | None]:
        """Search for a match ID by team names. Returns (match_id, match_name)."""
        result = self.cric_api._get("currentMatches", params={"offset": 0})
        if "error" in result:
            return None, None

        matches = result.get("data", [])
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]

        scored = []
        for m in matches:
            name = m.get("name", "").lower()
            score = sum(1 for w in query_words if w in name)
            if score == 0:
                continue

            # Penalize U19, Women, emerging unless query mentions them
            if "u19" in name and "u19" not in query_lower:
                score -= 2
            if "women" in name and "women" not in query_lower:
                score -= 2
            if "emerging" in name and "emerging" not in query_lower:
                score -= 1

            # Bonus for completed matches (have scorecards)
            if m.get("matchEnded"):
                score += 1

            scored.append((score, m))

        if not scored:
            return None, None

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        return best.get("id"), best.get("name")

    def _fetch_scorecard(self, match_id: str) -> dict | None:
        result = self.cric_api._get("match_scorecard", params={"id": match_id})
        if "error" in result:
            return None
        return result.get("data")

    def _analyze_batting(self, batting: list) -> list:
        """
        Find high-impact dismissals — batsmen who were scoring
        fast when dismissed, making their wicket a turning point.
        """
        impacts = []
        for b in batting:
            runs = b.get("r", 0)
            balls = b.get("b", 1)
            sr = b.get("sr", 0)
            dismissal = b.get("dismissal", "not out")
            name = b.get("batsman", {}).get("name", "Unknown")
            bowler = b.get("bowler", {}).get("name", "Unknown") if b.get("bowler") else None

            if dismissal == "not out" or balls == 0:
                continue

            impact_score = (runs * sr) / 100

            if impact_score > 10:
                impacts.append({
                    "batsman": name,
                    "runs": runs,
                    "balls": balls,
                    "sr": sr,
                    "bowler": bowler,
                    "dismissal": dismissal,
                    "impact_score": round(impact_score, 1),
                })

        impacts.sort(key=lambda x: x["impact_score"], reverse=True)
        return impacts[:3]

    def _analyze_bowling(self, bowling: list) -> list:
        """
        Find high-impact bowling spells — best wickets + economy combo.
        """
        impacts = []
        for b in bowling:
            overs = b.get("o", 0)
            runs = b.get("r", 0)
            wickets = b.get("w", 0)
            eco = b.get("eco", 0)
            name = b.get("bowler", {}).get("name", "Unknown")

            if overs == 0:
                continue

            impact_score = (wickets * 15) - (eco * 2)

            if wickets > 0:
                impacts.append({
                    "bowler": name,
                    "overs": overs,
                    "runs": runs,
                    "wickets": wickets,
                    "economy": eco,
                    "impact_score": round(impact_score, 1),
                })

        impacts.sort(key=lambda x: x["impact_score"], reverse=True)
        return impacts[:3]

    def _estimate_worm_data(self, batting: list, total_overs: float) -> list:
        """
        Estimate over-by-over cumulative runs from batting data.
        Since we don't have ball-by-ball data, we distribute runs
        proportionally based on powerplay/middle/death over patterns.
        """
        total_overs_int = int(total_overs)
        if total_overs_int == 0:
            return []

        total_runs = sum(b.get("r", 0) for b in batting)
        worm = []
        cumulative = 0

        for over in range(1, total_overs_int + 1):
            if over <= 6:
                over_runs = total_runs * 0.28 / 6
            elif over <= 15:
                over_runs = total_runs * 0.45 / 9
            else:
                death_overs = max(total_overs_int - 15, 1)
                over_runs = total_runs * 0.27 / death_overs

            cumulative += over_runs
            worm.append(round(cumulative))

        # Normalize to actual total
        if worm and worm[-1] > 0:
            scale = total_runs / worm[-1]
            worm = [round(r * scale) for r in worm]

        return worm

    def run(self, task: str) -> str:
        # Step 1: find match
        match_id, match_found_name = self._search_match(task)
        if not match_id:
            return "ImpactAgent: Could not find a recent match matching your query."

        logger.debug(f"[ImpactAgent] Analyzing: {match_found_name}")

        # Step 2: fetch scorecard
        scorecard_data = self._fetch_scorecard(match_id)
        if not scorecard_data:
            return "ImpactAgent: Could not fetch scorecard data."

        match_name = scorecard_data.get("name", "Unknown match")
        status = scorecard_data.get("status", "")
        scorecard = scorecard_data.get("scorecard", [])
        score = scorecard_data.get("score", [])

        if not scorecard:
            return f"ImpactAgent: No scorecard available for {match_name}."

        # Step 3: analyze both innings
        innings_analyses = []
        worm_data = {}

        for i, inning in enumerate(scorecard):
            batting = inning.get("batting", [])
            bowling = inning.get("bowling", [])

            inning_score = score[i] if i < len(score) else {}
            total_runs = inning_score.get("r", 0)
            total_wickets = inning_score.get("w", 0)
            total_overs = inning_score.get("o", 20)
            inning_name = inning_score.get("inning", f"Inning {i+1}")

            batting_impacts = self._analyze_batting(batting)
            bowling_impacts = self._analyze_bowling(bowling)
            worm = self._estimate_worm_data(batting, total_overs)

            team_name = inning_name.split()[0] if inning_name else f"Team {i+1}"
            worm_data[team_name] = worm

            innings_analyses.append({
                "inning": inning_name,
                "total": f"{total_runs}-{total_wickets} ({total_overs} ov)",
                "batting_impacts": batting_impacts,
                "bowling_impacts": bowling_impacts,
            })

        # Step 4: build summary for LLM
        summary = f"Match: {match_name}\nResult: {status}\n\n"

        for analysis in innings_analyses:
            summary += f"--- {analysis['inning']} ({analysis['total']}) ---\n"
            summary += "Key dismissals (most impactful):\n"
            for b in analysis["batting_impacts"]:
                summary += f"  {b['batsman']}: {b['runs']} runs off {b['balls']} balls (SR: {b['sr']}) dismissed by {b['bowler']}\n"
            summary += "Key bowling spells:\n"
            for b in analysis["bowling_impacts"]:
                summary += f"  {b['bowler']}: {b['wickets']}/{b['runs']} in {b['overs']} overs (eco: {b['economy']})\n"
            summary += "\n"

        # Step 5: LLM narrates the turning points
        narrative = invoke_llm(
            system_prompt=(
                "You are a cricket match analyst specializing in identifying turning points. "
                "Given the match scorecard analysis, identify 2-3 specific turning points. "
                "For each turning point state: which over (estimate), what happened, "
                "and how it shifted momentum. Be specific with player names and numbers. "
                "Format each turning point on a new line starting with 'TURNING POINT:'. "
                "End with one sentence on what ultimately decided the match."
            ),
            user_prompt=summary,
        )

        # Step 6: format output including worm data for Streamlit later
        output = f"""
=== IMPACT ANALYSIS: {match_name} ===
Result: {status}

{narrative}

=== WORM GRAPH DATA (for visualization) ===
{worm_data}

=== TOP BATTING IMPACTS ==="""

        for analysis in innings_analyses:
            output += f"\n{analysis['inning']} ({analysis['total']}):"
            for b in analysis["batting_impacts"]:
                output += f"\n  {b['batsman']}: {b['runs']}({b['balls']}) SR:{b['sr']} — dismissed by {b['bowler']} [impact: {b['impact_score']}]"

        output += "\n\n=== TOP BOWLING IMPACTS ==="
        for analysis in innings_analyses:
            output += f"\n{analysis['inning']}:"
            for b in analysis["bowling_impacts"]:
                output += f"\n  {b['bowler']}: {b['wickets']}/{b['runs']} ({b['overs']} ov) eco:{b['economy']}"

        return output