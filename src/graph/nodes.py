"""
LangGraph node functions for CricketIQ.

Each function represents a single node in the StateGraph. Every node:
  - Receives the full CricketIQState
  - Does its work (calls an agent, makes an LLM call, etc.)
  - Returns a dict with ONLY the keys it wants to update in state

LangGraph merges returned dicts back into the shared state automatically.
"""

import asyncio
import ollama

from src.config import Config
from src.graph.state import CricketIQState
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS

# Lazy-import agents so they are only instantiated when needed
from src.agents.cricket import CricketAgent
from src.agents.bowler import BowlerAgent
from src.agents.matchups import MatchupAgent
from src.agents.weather import WeatherAgent
from src.agents.pitch import PitchAgent
from src.agents.live_match import LiveMatchAgent
from src.agents.matchup_predictor import MatchupPredictorAgent

# ---------------------------------------------------------------------------
# Agent singletons (instantiated once per process for efficiency)
# ---------------------------------------------------------------------------
_cricket_agent           = CricketAgent()
_bowler_agent            = BowlerAgent()
_matchup_agent           = MatchupAgent()
_weather_agent           = WeatherAgent()
_pitch_agent             = PitchAgent()
_live_match_agent        = LiveMatchAgent()
_matchup_predictor_agent = MatchupPredictorAgent()

_config = Config()

# ---------------------------------------------------------------------------
# SUPERVISOR NODE
# ---------------------------------------------------------------------------

async def supervisor_node(state: CricketIQState) -> dict:
    """
    Rule-based supervisor.
    Decides which specialist agents to run without using an LLM.
    """

    query = state["query"].lower()
    planned = []

    # Batter detection
    if any(player.lower() in query for player in PLAYER_STATS):
        planned.append("CricketAgent")

    # Bowler detection
    if any(bowler.lower() in query for bowler in BOWLER_STATS):
        planned.append("BowlerAgent")

    # Matchup analysis
    if "CricketAgent" in planned and "BowlerAgent" in planned:
        planned.append("MatchupAgent")
        planned.append("MatchupPredictorAgent")

    # Venue detection
    if any(venue.lower() in query for venue in PITCH_CONDITIONS):
        planned.append("WeatherAgent")
        planned.append("PitchAgent")

    # Live match detection
    if any(word in query for word in ["live", "score", "schedule", "upcoming", "completed", "recent", "result", "results", "won", "finished", "yesterday"]):
        planned.append("LiveMatchAgent")

    print(f"\n[Supervisor] Routing to: {planned}")

    return {"planned_agents": planned}

# ---------------------------------------------------------------------------
# SPECIALIST AGENT NODES
# ---------------------------------------------------------------------------

async def cricket_node(state: CricketIQState) -> dict:
    """Batting statistics and form analysis."""
    result = await asyncio.to_thread(_cricket_agent.run, state["query"])
    print(f"[CricketAgent] Done.")
    return {"agent_outputs": {"CricketAgent": result}}


async def bowler_node(state: CricketIQState) -> dict:
    """Bowling threat analysis — one call handles all bowlers in the query."""
    query = state["query"]
    query_lower = query.lower()

    # Find all bowlers mentioned; run analysis for each
    mentioned_bowlers = [b for b in BOWLER_STATS if b in query_lower]
    if not mentioned_bowlers:
        mentioned_bowlers = list(BOWLER_STATS.keys())[:1]

    tasks = [
        asyncio.to_thread(_bowler_agent.run, f"bowling analysis for {bowler} vs batter in: {query}")
        for bowler in mentioned_bowlers
    ]
    outputs = await asyncio.gather(*tasks)

    combined = "\n\n".join(outputs)
    print(f"[BowlerAgent] Done ({len(mentioned_bowlers)} bowler(s)).")
    return {"agent_outputs": {"BowlerAgent": combined}}


async def matchup_node(state: CricketIQState) -> dict:
    """Batter vs bowler(s) matchup and tactical analysis."""
    result = await asyncio.to_thread(_matchup_agent.run, state["query"])
    print(f"[MatchupAgent] Done.")
    return {"agent_outputs": {"MatchupAgent": result}}


async def matchup_predictor_node(state: CricketIQState) -> dict:
    """Predict batsman success probabilities and metrics against bowler."""
    result = await asyncio.to_thread(_matchup_predictor_agent.run, state["query"])
    print(f"[MatchupPredictorAgent] Done.")
    return {"agent_outputs": {"MatchupPredictorAgent": result}}


async def weather_node(state: CricketIQState) -> dict:
    """Real-time weather conditions and impact analysis for the venue."""
    result = await asyncio.to_thread(_weather_agent.run, state["query"])
    print(f"[WeatherAgent] Done.")
    return {"agent_outputs": {"WeatherAgent": result}}


async def pitch_node(state: CricketIQState) -> dict:
    """Pitch conditions and tactical surface analysis."""
    result = await asyncio.to_thread(_pitch_agent.run, state["query"])
    print(f"[PitchAgent] Done.")
    return {"agent_outputs": {"PitchAgent": result}}


async def live_match_node(state: CricketIQState) -> dict:
    """Live scores and upcoming match schedule."""
    result = await asyncio.to_thread(_live_match_agent.run, state["query"])
    print(f"[LiveMatchAgent] Done.")
    return {"agent_outputs": {"LiveMatchAgent": result}}


# ---------------------------------------------------------------------------
# AGGREGATOR NODE
# ---------------------------------------------------------------------------

async def aggregator_node(state: CricketIQState) -> dict:
    """
    Receives all agent outputs from state and generates the final
    CricketIQ report using an LLM synthesis call.
    """
    agent_outputs = state.get("agent_outputs", {})
    query = state["query"]

    if not agent_outputs:
        return {"final_report": "No agent outputs available to aggregate."}

    # Build a combined context string
    combined = "\n\n".join(
        f"--- {agent} Output ---\n{output}"
        for agent, output in agent_outputs.items()
    )

    # Dynamically build the system prompt based on which agents ran
    active_agents = list(agent_outputs.keys())
    sections = ["1) Overall verdict on the batter's current form."]
    if "BowlerAgent" in active_agents:
        sections.append("2) Which bowler poses the biggest threat and why.")
    if "MatchupAgent" in active_agents:
        sections.append("3) The key matchup to watch.")
    if "MatchupPredictorAgent" in active_agents:
        sections.append(f"{len(sections) + 1}) The detailed match dominance and dismissal probabilities with tactical explanation.")
    if "PitchAgent" in active_agents:
        sections.append(f"{len(sections) + 1}) How the pitch surface affects the contest.")
    if "WeatherAgent" in active_agents:
        sections.append(f"{len(sections) + 1}) How weather conditions affect the match.")
    if "LiveMatchAgent" in active_agents:
        sections.append(f"{len(sections) + 1}) Current live match or schedule context.")
    sections.append(f"{len(sections) + 1}) A final prediction — will the batter score well?")

    sections_text = "\n".join(sections)

    response = await asyncio.to_thread(
        ollama.chat,
        model=_config.OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the final aggregator for CricketIQ. "
                    "You receive outputs from specialist cricket analysis agents. "
                    f"Write a clear, confident final report in 6-8 sentences covering:\n"
                    f"{sections_text}\n"
                    "Sound like a senior analyst presenting to a team selection committee. "
                    "Be specific with numbers from the data."
                ),
            },
            {
                "role": "user",
                "content": f"User question: {query}\n\nAgent outputs:\n{combined}",
            },
        ],
    )

    final = response["message"]["content"]
    print(f"[Aggregator] Report generated.")

    separator = "=" * 60
    predictor_output = agent_outputs.get("MatchupPredictorAgent", "")
    
    if predictor_output:
        report = f"""
{separator}
  CRICKETIQ FINAL REPORT
{separator}

{final}

{predictor_output}

{separator}
"""
    else:
        report = f"""
{separator}
  CRICKETIQ FINAL REPORT
{separator}

{final}

{separator}
"""
    return {"final_report": report}
