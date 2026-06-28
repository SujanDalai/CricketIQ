import ollama
from src.agents.base import BaseAgent
from src.tools.cricket_data import PITCH_CONDITIONS
from src.config import Config


class PitchAgent(BaseAgent):
    """
    Pitch Agent analyzes pitch conditions for a given venue and produces
    tactical recommendations on how the surface affects team selection
    and match strategy.
    """

    def __init__(self):
        super().__init__(name="PitchAgent", role="Pitch Conditions and Tactical Analysis")
        self.config = Config()

    def _find_venue(self, task_lower: str) -> str | None:
        for venue in PITCH_CONDITIONS.keys():
            if venue in task_lower:
                return venue
        return None

    def _score_pitch(self, conditions: dict) -> dict:
        """
        Convert qualitative pitch descriptors into numerical scores and
        a batting/bowling suitability index.
        """
        level_map = {"low": 1, "medium": 2, "high": 3}

        pace   = level_map.get(conditions.get("pace",   "medium"), 2)
        bounce = level_map.get(conditions.get("bounce", "medium"), 2)
        spin   = level_map.get(conditions.get("spin",   "medium"), 2)
        swing  = level_map.get(conditions.get("swing",  "medium"), 2)

        # Bowling difficulty index (higher = harder for batters)
        bowling_index = round((pace + bounce + swing + spin) / 12 * 10, 1)
        batting_index = round(10 - bowling_index, 1)

        return {
            "bowling_index": bowling_index,
            "batting_index": batting_index,
            "dominant_factor": max(
                {"pace": pace, "bounce": bounce, "spin": spin, "swing": swing},
                key=lambda k: {"pace": pace, "bounce": bounce, "spin": spin, "swing": swing}[k]
            ),
        }

    def run(self, task: str) -> str:
        task_lower = task.lower()
        venue = self._find_venue(task_lower)

        if not venue:
            return "PitchAgent: Could not identify a venue in the task."

        conditions = PITCH_CONDITIONS[venue]
        scores = self._score_pitch(conditions)

        pitch_summary = f"""
Venue   : {venue.title()}
Pace    : {conditions['pace']}
Bounce  : {conditions['bounce']}
Spin    : {conditions['spin']}
Swing   : {conditions['swing']}
Favours : {conditions['favours']}

Bowling Index : {scores['bowling_index']}/10  (higher = harder for batters)
Batting Index : {scores['batting_index']}/10
Dominant Factor: {scores['dominant_factor'].title()}
"""

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior pitch consultant for a professional cricket team. "
                        "Given the following pitch data, write a 3-4 sentence tactical analysis. "
                        "State clearly whether it favours batters or bowlers, which type of bowling "
                        "will be most effective, and one key team selection implication. "
                        "Be sharp and specific — this will go to the team management."
                    ),
                },
                {"role": "user", "content": pitch_summary},
            ],
        )

        llm_analysis = response["message"]["content"]

        return f"""
=== PITCH ANALYSIS: {venue.title()} ===
Pace          : {conditions['pace'].upper()}
Bounce        : {conditions['bounce'].upper()}
Spin          : {conditions['spin'].upper()}
Swing         : {conditions['swing'].upper()}
Favours       : {conditions['favours'].title()}
Bowling Index : {scores['bowling_index']}/10
Batting Index : {scores['batting_index']}/10

TACTICAL ASSESSMENT:
{llm_analysis}
"""
