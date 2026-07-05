from src.agents.base import BaseAgent


class HistoricalMatchAgent(BaseAgent):
    """
    Handles historical cricket match queries.
    """

    def __init__(self):
        super().__init__(
            name="HistoricalMatchAgent",
            role="Historical Cricket Matches"
        )

    def run(self, task: str) -> str:
        return (
            "🏏 Historical Match Agent\n\n"
            f"Query: {task}\n\n"
            "Historical match retrieval is under development."
        )