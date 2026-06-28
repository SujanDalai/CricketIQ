import json
import ollama
from src.config import Config
from src.agents.base import BaseAgent
from src.agents.cricket import CricketAgent
from src.agents.bowler import BowlerAgent
from src.agents.matchups import MatchupAgent
from src.agents.weather import WeatherAgent
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent oversees the user request, delegates subtasks
    to specialist agents, then aggregates a final response.
    """

    def __init__(self):
        super().__init__(name="CoordinatorAgent", role="Orchestration and Aggregation")
        self.config = Config()
        self.cricket_agent  = CricketAgent()
        self.bowler_agent   = BowlerAgent()
        self.matchup_agent  = MatchupAgent()
        self.weather_agent  = WeatherAgent()

    def _plan_tasks(self, user_query: str) -> list:
        """
        Use Ollama to break the user query into structured subtasks.
        Returns a list of task dicts with 'agent' and 'task' keys.
        """
        known_batters  = list(PLAYER_STATS.keys())
        known_bowlers  = list(BOWLER_STATS.keys())
        known_venues   = list(PITCH_CONDITIONS.keys())

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the coordinator of CricketIQ, a cricket analytics system. "
                        "Given a user query, output ONLY a JSON array of task objects. "
                        "Each object must have exactly two keys: 'agent' and 'task'. "
                        f"'agent' must be one of: CricketAgent, BowlerAgent, MatchupAgent, WeatherAgent. "
                        f"Known batters: {known_batters}. "
                        f"Known bowlers: {known_bowlers}. "
                        f"Known venues: {known_venues}. "
                        "Rules: "
                        "- Always include one CricketAgent task for the batter. "
                        "- Include one BowlerAgent task per bowler mentioned. "
                        "- Include one MatchupAgent task that lists all bowlers and the batter together. "
                        "- If a venue is mentioned, ALWAYS include one WeatherAgent task for that venue. "
                        "- The WeatherAgent task string must include the venue name. "
                        "- The MatchupAgent task string must include the batter name, all bowler names, venue if mentioned, and format if mentioned. "
                        "Example output for 'Will Kohli score vs Starc and Cummins at Perth in Test?': "
                        '[{"agent": "CricketAgent", "task": "batting form analysis for virat kohli"}, '
                        '{"agent": "BowlerAgent", "task": "bowling analysis for mitchell starc vs virat kohli"}, '
                        '{"agent": "BowlerAgent", "task": "bowling analysis for pat cummins vs virat kohli"}, '
                        '{"agent": "MatchupAgent", "task": "matchup analysis virat kohli vs mitchell starc pat cummins at perth test"}, '
                        '{"agent": "WeatherAgent", "task": "weather analysis for perth"}] '
                        "Output ONLY the JSON array. No explanation. No markdown."
                    ),
                },
                {"role": "user", "content": user_query},
            ],
        )

        raw = response["message"]["content"].strip()

        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            tasks = json.loads(raw.strip())
            if isinstance(tasks, list):
                return tasks
        except Exception:
            pass

        # Fallback: basic single task
        return [{"agent": "CricketAgent", "task": f"batting analysis for player in: {user_query}"}]

    def _run_task(self, agent_name: str, task: str) -> str:
        if agent_name == "CricketAgent":
            return self.cricket_agent.run(task)
        elif agent_name == "BowlerAgent":
            return self.bowler_agent.run(task)
        elif agent_name == "MatchupAgent":
            return self.matchup_agent.run(task)
        elif agent_name == "WeatherAgent":
            return self.weather_agent.run(task)
        else:
            return f"Unknown agent: {agent_name}"

    def _aggregate(self, user_query: str, agent_outputs: list) -> str:
        combined = "\n\n".join(
            f"--- {output['agent']} Output ---\n{output['result']}"
            for output in agent_outputs
        )

        response = ollama.chat(
            model=self.config.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the final aggregator for CricketIQ. "
                        "You receive outputs from specialist cricket analysis agents: "
                        "a batting analyst, a bowling analyst, a matchup tactician, and a weather analyst. "
                        "Write a clear, confident final report in 6-8 sentences covering: "
                        "1) Overall verdict on the batter's current form. "
                        "2) Which bowler poses the biggest threat and why. "
                        "3) The key matchup to watch. "
                        "4) How weather conditions affect the match — do they favour batting or bowling? "
                        "5) A final prediction — will the batter score well? "
                        "Sound like a senior analyst presenting to a team selection committee. "
                        "Be specific with numbers from the data."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User question: {user_query}\n\nAgent outputs:\n{combined}",
                },
            ],
        )

        return response["message"]["content"]

    def run(self, task: str) -> str:
        print(f"\n[Coordinator] Received query: {task}")

        # Step 1: Plan tasks
        print("[Coordinator] Planning subtasks...")
        subtasks = self._plan_tasks(task)
        print(f"[Coordinator] Subtasks planned: {len(subtasks)}")
        for t in subtasks:
            print(f"  → [{t.get('agent')}] {t.get('task')}")

        # Step 2: Run each agent
        agent_outputs = []
        for subtask in subtasks:
            agent_name = subtask.get("agent", "CricketAgent")
            agent_task = subtask.get("task", task)
            print(f"\n[{agent_name}] Running: {agent_task}")
            result = self._run_task(agent_name, agent_task)
            print(result)
            agent_outputs.append({"agent": agent_name, "result": result})

        # Step 3: Aggregate
        print("\n[Coordinator] Aggregating final report...")
        final_report = self._aggregate(task, agent_outputs)

        return f"""
{'='*60}
  CRICKETIQ FINAL REPORT
{'='*60}

{final_report}

{'='*60}
"""
