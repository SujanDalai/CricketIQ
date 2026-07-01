"""
LangGraph node functions for CricketIQ.

Each function represents a single node in the StateGraph. Every node:
  - Receives the full CricketIQState
  - Does its work (calls an agent, makes an LLM call, etc.)
  - Returns a dict with ONLY the keys it wants to update in state

LangGraph merges returned dicts back into the shared state automatically.
"""

import asyncio
from src.llm.client import invoke_llm
from src.graph.state import CricketIQState
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS

from src.agents.cricket import CricketAgent
from src.agents.bowler import BowlerAgent
from src.agents.matchups import MatchupAgent
from src.agents.weather import WeatherAgent
from src.agents.pitch import PitchAgent
from src.agents.live_match import LiveMatchAgent
from src.agents.matchup_predictor import MatchupPredictorAgent

# ---------------------------------------------------------------------------
# Agent singletons
# ---------------------------------------------------------------------------
_cricket_agent           = CricketAgent()
_bowler_agent            = BowlerAgent()
_matchup_agent           = MatchupAgent()
_weather_agent           = WeatherAgent()
_pitch_agent             = PitchAgent()
_live_match_agent        = LiveMatchAgent()
_matchup_predictor_agent = MatchupPredictorAgent()


# ---------------------------------------------------------------------------
# SUPERVISOR NODE
# ---------------------------------------------------------------------------

async def supervisor_node(state: CricketIQState) -> dict:
    query = state["query"].lower()
    planned = []

    # Batter detection
    for player in PLAYER_STATS:
        parts = player.split()
        if player in query or any(p in query for p in parts if len(p) > 3):
            planned.append("CricketAgent")
            break

    # Bowler detection
    for bowler in BOWLER_STATS:
        parts = bowler.split()
        if bowler in query or any(p in query for p in parts if len(p) > 3):
            planned.append("BowlerAgent")
            break

    # Matchup analysis — only if both batter and bowler found
    if "CricketAgent" in planned and "BowlerAgent" in planned:
        planned.append("MatchupAgent")
        planned.append("MatchupPredictorAgent")

    # Venue detection
    for venue in PITCH_CONDITIONS:
        if venue in query:
            planned.append("WeatherAgent")
            planned.append("PitchAgent")
            break

    # Historical query — do NOT route to LiveMatchAgent
    historical_keywords = [
        "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023",
        "scorecard", "semifinal", "final", "world cup"
    ]
    is_historical = any(word in query for word in historical_keywords)

    # Live match detection — only if not historical
    live_keywords = [
        "live match", "live score", "schedule", "upcoming match",
        "completed match", "recent match", "latest result", "won by",
        "finished yesterday", "result of", "who won"
    ]
    if not is_historical and any(word in query for word in live_keywords):
        planned.append("LiveMatchAgent")
    # Stats query — fire CricketAgent even for unknown players
    stats_keywords = ["stats", "average", "record", "career", "centuries", "how many runs", "batting average", "ipl"]
    if any(word in query for word in stats_keywords):
        if "CricketAgent" not in planned:
            planned.append("CricketAgent")

    # Fallback for general match questions
    if not planned:
        live_hint_keywords = ["win", "today", "tonight", "match", "playing", "which team"]
        if any(word in query for word in live_hint_keywords):
            planned.append("LiveMatchAgent")

    print(f"\n[Supervisor] Routing to: {planned}")
    return {"planned_agents": planned}


# ---------------------------------------------------------------------------
# SPECIALIST AGENT NODES
# ---------------------------------------------------------------------------

async def cricket_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_cricket_agent.run, state["query"])
    print(f"[CricketAgent] Done.")
    return {"agent_outputs": {"CricketAgent": result}}


async def bowler_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()

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
    result = await asyncio.to_thread(_matchup_agent.run, state["query"])
    print(f"[MatchupAgent] Done.")
    return {"agent_outputs": {"MatchupAgent": result}}


async def matchup_predictor_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_matchup_predictor_agent.run, state["query"])
    print(f"[MatchupPredictorAgent] Done.")
    return {"agent_outputs": {"MatchupPredictorAgent": result}}


async def weather_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_weather_agent.run, state["query"])
    print(f"[WeatherAgent] Done.")
    return {"agent_outputs": {"WeatherAgent": result}}


async def pitch_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_pitch_agent.run, state["query"])
    print(f"[PitchAgent] Done.")
    return {"agent_outputs": {"PitchAgent": result}}


async def live_match_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_live_match_agent.run, state["query"])
    print(f"[LiveMatchAgent] Done.")
    return {"agent_outputs": {"LiveMatchAgent": result}}


# ---------------------------------------------------------------------------
# AGGREGATOR NODE
# ---------------------------------------------------------------------------

async def aggregator_node(state: CricketIQState) -> dict:
    agent_outputs = state.get("agent_outputs", {})
    query = state["query"]

    if not agent_outputs:
        return {"final_report": "No agent outputs available to aggregate."}

    combined = "\n\n".join(
        f"--- {agent} Output ---\n{output}"
        for agent, output in agent_outputs.items()
    )

    active_agents = list(agent_outputs.keys())
    sections = []

    if "CricketAgent" in active_agents:
        sections.append(f"{len(sections)+1}) Overall verdict on the batter's current form.")
    if "BowlerAgent" in active_agents:
        sections.append(f"{len(sections)+1}) Which bowler poses the biggest threat and why.")
    if "MatchupAgent" in active_agents:
        sections.append(f"{len(sections)+1}) The key matchup to watch.")
    if "MatchupPredictorAgent" in active_agents:
        sections.append(f"{len(sections)+1}) Dismissal and batting dominance probabilities.")
    if "PitchAgent" in active_agents:
        sections.append(f"{len(sections)+1}) How the pitch surface affects the contest.")
    if "WeatherAgent" in active_agents:
        sections.append(f"{len(sections)+1}) How weather conditions affect the match.")
    if "LiveMatchAgent" in active_agents:
        sections.append(f"{len(sections)+1}) Current live match or schedule context.")

    sections_text = "\n".join(sections)

    final = await asyncio.to_thread(
        invoke_llm,
        system_prompt=(
            "You are the final aggregator for CricketIQ. "
            "You receive outputs from specialist cricket analysis agents. "
            "IMPORTANT: Only use data provided by the agents. Never invent statistics, "
            "scores, or predictions not present in the agent outputs. "
            "If data is insufficient to answer the question, say so clearly. "
            f"Write a clear, confident final report in 6-8 sentences covering:\n"
            f"{sections_text}\n"
            "Sound like a senior analyst presenting to a team selection committee. "
            "Be specific with numbers from the data."
        ),
        user_prompt=f"User question: {query}\n\nAgent outputs:\n{combined}",
    )
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