from src.agents.base import BaseAgent
from src.tools.cric_api import CricAPI
from src.tools.cricbuzz import CricbuzzScraper
from src.llm.client import invoke_llm
from src.config import Config


class LiveMatchAgent(BaseAgent):
    """
    Live Match Agent fetches real-time cricket match data — live scores and
    upcoming schedules — primarily using cricbuzz.com scraping and falling
    back to CricAPI if needed.
    """

    def __init__(self):
        super().__init__(name="LiveMatchAgent", role="Live Scores and Match Schedules")
        config = Config()
        self.cric_api = CricAPI(config.CRIC_API_KEY)
        self.cricbuzz_scraper = CricbuzzScraper()

    def run(self, task: str) -> str:
        task_lower = task.lower()

        is_live = any(kw in task_lower for kw in [
            "live", "score", "playing", "happening", "now", "completed",
            "recent", "result", "results", "won", "yesterday", "finished"
        ])
        mode = "LIVE SCORES" if is_live else "UPCOMING SCHEDULE"

        if is_live:
            data = self.cricbuzz_scraper.get_live_scores()
        else:
            data = self.cricbuzz_scraper.get_match_schedule()

        has_error = isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "error" in data[0]

        if has_error:
            cricbuzz_error = data[0]["error"]
            print(f"[LiveMatchAgent] Cricbuzz failed ({cricbuzz_error}), falling back to CricAPI...")
            if is_live:
                data = self.cric_api.get_live_scores()
            else:
                data = self.cric_api.get_match_schedule()

        if (isinstance(data, dict) and "error" in data) or \
           (isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "error" in data[0]):
            error_msg = data["error"] if isinstance(data, dict) else data[0]["error"]
            return (
                f"=== LIVE MATCH AGENT: {mode} ===\n"
                f"Status: Unavailable ({error_msg})\n"
                "Note: Configure CRIC_API_KEY in your .env or check network connection."
            )

        if not data:
            return (
                f"=== LIVE MATCH AGENT: {mode} ===\n"
                "No matches found at this time."
            )

        matches_text = ""
        for i, m in enumerate(data[:5], 1):
            matches_text += f"\nMatch {i}: {m.get('name', 'Unknown')}\n"
            if m.get("status"):
                matches_text += f"  Status : {m['status']}\n"
            if m.get("venue"):
                matches_text += f"  Venue  : {m['venue']}\n"
            if m.get("date"):
                matches_text += f"  Date   : {m['date']}\n"
            if m.get("score"):
                matches_text += f"  Score  : {m['score']}\n"
            if m.get("teams"):
                matches_text += f"  Teams  : {' vs '.join(m['teams'])}\n"

        llm_summary = invoke_llm(
            system_prompt=(
                "You are a live cricket commentator. "
                "Given the following match data, give a 2-3 sentence update. "
                "Mention the key matches happening, teams involved, and current status. "
                "Be concise and energetic — like a sports desk update."
            ),
            user_prompt=matches_text,
        )

        return f"""
=== LIVE MATCH AGENT: {mode} ===
{matches_text}
SUMMARY:
{llm_summary}
"""