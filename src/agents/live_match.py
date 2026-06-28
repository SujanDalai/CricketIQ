import ollama
from src.agents.base import BaseAgent
from src.tools.cric_api import CricAPI
from src.config import Config


class LiveMatchAgent(BaseAgent):
    """
    Live Match Agent fetches real-time cricket match data — live scores and
    upcoming schedules — using the CricAPI wrapper.
    Falls back to a clear message if the API key is not configured.
    """

    def __init__(self):
        super().__init__(name="LiveMatchAgent", role="Live Scores and Match Schedules")
        self.config = Config()
        self.cric_api = CricAPI(self.config.CRIC_API_KEY)

    def run(self, task: str) -> str:
        task_lower = task.lower()

        # Decide whether to fetch live scores or schedule
        if any(kw in task_lower for kw in ["live", "score", "playing", "happening", "now"]):
            data = self.cric_api.get_live_scores()
            mode = "LIVE SCORES"
        else:
            data = self.cric_api.get_match_schedule()
            mode = "UPCOMING SCHEDULE"

        # Handle API errors gracefully
        if isinstance(data, dict) and "error" in data:
            error_msg = data["error"]
            return (
                f"=== LIVE MATCH AGENT: {mode} ===\n"
                f"Status: Unavailable ({error_msg})\n"
                "Note: Configure CRIC_API_KEY in your .env to enable live data."
            )

        if not data:
            return (
                f"=== LIVE MATCH AGENT: {mode} ===\n"
                "No matches found at this time."
            )

        # Format match list for LLM narration
        matches_text = ""
        for i, m in enumerate(data[:5], 1):  # cap at 5 matches
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

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a live cricket commentator. "
                        "Given the following match data, give a 2-3 sentence update. "
                        "Mention the key matches happening, teams involved, and current status. "
                        "Be concise and energetic — like a sports desk update."
                    ),
                },
                {"role": "user", "content": matches_text},
            ],
        )

        llm_summary = response["message"]["content"]

        return f"""
=== LIVE MATCH AGENT: {mode} ===
{matches_text}
SUMMARY:
{llm_summary}
"""
