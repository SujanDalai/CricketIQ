"""
LangGraph node functions for CricketIQ.

Each function represents a single node in the StateGraph. Every node:
  - Receives the full CricketIQState
  - Does its work (calls an agent, makes an LLM call, etc.)
  - Returns a dict with ONLY the keys it wants to update in state

LangGraph merges returned dicts back into the shared state automatically.
"""

import asyncio
import json
from src.llm.client import invoke_llm
from src.graph.state import CricketIQState
from src.tools.cricket_data import PLAYER_STATS, BOWLER_STATS, PITCH_CONDITIONS
from src.tools.cric_api import CricAPI
from src.config import Config

from src.agents.cricket import CricketAgent
from src.agents.bowler import BowlerAgent
from src.agents.matchups import MatchupAgent
from src.agents.weather import WeatherAgent
from src.agents.pitch import PitchAgent
from src.agents.live_match import LiveMatchAgent
from src.agents.matchup_predictor import MatchupPredictorAgent
from src.agents.impact import ImpactAgent

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
_impact_agent            = ImpactAgent()
_cric_api                = CricAPI(Config().CRIC_API_KEY)


# ---------------------------------------------------------------------------
# SUPERVISOR NODE
# ---------------------------------------------------------------------------

async def supervisor_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()

    historical_keywords = [
        "2003", "2007", "2008", "2009", "2010", "2011", "2012", "2013",
        "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021",
        "2022", "2023", "scorecard", "semifinal", "world cup"
    ]
    is_historical = any(word in query_lower for word in historical_keywords)

    classification = await asyncio.to_thread(
        invoke_llm,
        system_prompt=(
            "You are a cricket query classifier. Analyze the query and return a JSON object.\n"
            "Fields:\n"
            "- 'batter': full name of the batter in the query (null if none)\n"
            "- 'bowler': full name of the bowler in the query (null if none)\n"
            "- 'venue': venue/ground name (null if none)\n"
            "- 'format': 'Test', 'ODI', 'T20I', or null\n"
            "- 'intent': one of: 'player_stats', 'matchup', 'live_scores', 'pitch_weather', 'impact_analysis', 'general'\n"
            "- 'is_live': true if asking about current/live/recent matches\n"
            "- 'is_historical': true if asking about past matches with specific years\n\n"
            "For 'X vs Y' queries, use cricket knowledge to determine who is batter and bowler.\n"
            "Examples:\n"
            "- 'Malinga vs Sachin' → batter='Sachin Tendulkar', bowler='Lasith Malinga'\n"
            "- 'Kohli vs Starc' → batter='Virat Kohli', bowler='Mitchell Starc'\n"
            "- 'Bhuvneshwar vs Abhishek Sharma' → batter='Abhishek Sharma', bowler='Bhuvneshwar Kumar'\n"
            "- 'show me live scores' → intent='live_scores', is_live=true\n"
            "- 'how is kohli batting' → intent='player_stats', batter='Virat Kohli'\n"
            "- 'what was the turning point in today match' → intent='impact_analysis'\n"
            "Return ONLY valid JSON, no explanation, no markdown backticks."
        ),
        user_prompt=f"Query: {query}"
    )

    try:
        clean = classification.strip().strip("```json").strip("```").strip()
        parsed = json.loads(clean)
    except Exception:
        parsed = {}

    batter = parsed.get("batter")
    bowler = parsed.get("bowler")
    venue = parsed.get("venue")
    intent = parsed.get("intent", "general")
    is_live = parsed.get("is_live", False)

    print(f"[Supervisor] Intent: {intent} | Batter: {batter} | Bowler: {bowler} | Venue: {venue}")

    planned = []
    vs_batter_hint = batter or ""
    vs_bowler_hint = bowler or ""

    if intent == "player_stats" or batter:
        planned.append("CricketAgent")

    if intent == "matchup" or bowler:
        planned.append("BowlerAgent")

    if batter and bowler:
        planned.append("MatchupAgent")
        planned.append("MatchupPredictorAgent")

    if intent == "impact_analysis":
        planned.append("ImpactAgent")

    if venue:
        planned.append("WeatherAgent")
        planned.append("PitchAgent")

    if (is_live or intent == "live_scores") and not is_historical:
        planned.append("LiveMatchAgent")

    if is_historical and not planned:
        planned.append("CricketAgent")

    if not planned:
        planned.append("LiveMatchAgent")

    planned = list(dict.fromkeys(planned))

    print(f"[Supervisor] Routing to: {planned}")

    result = {
        "planned_agents": planned,
        "batter_name": batter or "",
        "bowler_name": bowler or "",
        "venue": venue or "Unknown",
        "format": parsed.get("format") or "Overall Career",
    }
    if vs_batter_hint:
        result["vs_batter_hint"] = vs_batter_hint
    if vs_bowler_hint:
        result["vs_bowler_hint"] = vs_bowler_hint
    return result


# ---------------------------------------------------------------------------
# SPECIALIST AGENT NODES
# ---------------------------------------------------------------------------

async def cricket_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()
    vs_hint = state.get("vs_batter_hint", "")
    batter_stats = state.get("batter_stats")
    print(f"[CricketNode] vs_batter_hint from state: '{vs_hint}'")

    # Resolve batter name if missing
    if not vs_hint:
        for name in PLAYER_STATS.keys():
            if name.lower() in query_lower:
                vs_hint = name
                break
        if not vs_hint:
            for name in PLAYER_STATS.keys():
                parts = name.split()
                if any(p in query_lower for p in parts if len(p) > 3):
                    vs_hint = name
                    break
        if not vs_hint:
            vs_hint = _cricket_agent._extract_player_name(query_lower)

    # Fetch stats if missing
    if vs_hint and (not batter_stats or "error" in batter_stats):
        res = _cric_api.get_player_stats(vs_hint)
        if "error" not in res:
            batter_stats = res

    result = await asyncio.to_thread(
        _cricket_agent.run,
        task=query,
        player_name=vs_hint,
        batter_stats=batter_stats
    )
    print(f"[CricketAgent] Done.")
    return {
        "agent_outputs": {"CricketAgent": result},
        "batter_stats": batter_stats
    }


async def bowler_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()
    vs_hint = state.get("vs_bowler_hint", "")
    bowler_stats = state.get("bowler_stats")
    print(f"[BowlerNode] vs_bowler_hint from state: '{vs_hint}'")

    mentioned_bowlers = [b for b in BOWLER_STATS if b in query_lower]

    if mentioned_bowlers:
        # Pre-fetch if bowler_stats is missing for the first mentioned bowler
        first_bowler = mentioned_bowlers[0]
        if not bowler_stats or "error" in bowler_stats:
            res = _cric_api.get_player_stats(first_bowler)
            if "error" not in res:
                bowler_stats = res

        tasks = []
        for bowler in mentioned_bowlers:
            cached_stats = None
            if bowler_stats and bowler.lower() in bowler_stats.get("name", "").lower():
                cached_stats = bowler_stats
            tasks.append(
                asyncio.to_thread(
                    _bowler_agent.run,
                    task=query,
                    bowler_name=bowler,
                    bowler_stats=cached_stats
                )
            )
        outputs = await asyncio.gather(*tasks)
        combined = "\n\n".join(outputs)
        print(f"[BowlerAgent] Done.")
        return {
            "agent_outputs": {"BowlerAgent": combined},
            "bowler_stats": bowler_stats
        }
    else:
        # Fallback to vs_hint or resolve bowler name
        if not vs_hint:
            for bowler in BOWLER_STATS:
                parts = bowler.split()
                if bowler in query_lower or any(p in query_lower for p in parts if len(p) > 3):
                    vs_hint = bowler
                    break
            if not vs_hint:
                vs_hint = _bowler_agent._extract_bowler_name(query_lower)

        if vs_hint and (not bowler_stats or "error" in bowler_stats):
            res = _cric_api.get_player_stats(vs_hint)
            if "error" not in res:
                bowler_stats = res

        combined = await asyncio.to_thread(
            _bowler_agent.run,
            task=query,
            bowler_name=vs_hint,
            bowler_stats=bowler_stats
        )
        print(f"[BowlerAgent] Done.")
        return {
            "agent_outputs": {"BowlerAgent": combined},
            "bowler_stats": bowler_stats
        }


async def matchup_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()
    
    batter = state.get("vs_batter_hint", "")
    bowler = state.get("vs_bowler_hint", "")
    batter_stats = state.get("batter_stats")
    bowler_stats = state.get("bowler_stats")

    # Resolve names if missing
    if not batter or not bowler:
        ext_batter, ext_bowler = _matchup_predictor_agent._extract_names(query_lower)
        if not batter:
            batter = ext_batter
        if not bowler:
            bowler = ext_bowler

    result = await asyncio.to_thread(
        _matchup_agent.run,
        task=query,
        batter_stats=batter_stats,
        bowler_stats=bowler_stats
    )
    print(f"[MatchupAgent] Done.")
    return {
        "agent_outputs": {"MatchupAgent": result}
    }


async def matchup_predictor_node(state: CricketIQState) -> dict:
    query = state["query"]
    query_lower = query.lower()

    batter = state.get("vs_batter_hint", "")
    bowler = state.get("vs_bowler_hint", "")
    batter_stats = state.get("batter_stats")
    bowler_stats = state.get("bowler_stats")
    venue = state.get("venue", "Unknown")
    fmt = state.get("format", "Overall Career")

    # Resolve names if missing
    if not batter or not bowler:
        ext_batter, ext_bowler = _matchup_predictor_agent._extract_names(query_lower)
        if not batter:
            batter = ext_batter
        if not bowler:
            bowler = ext_bowler

    result = await asyncio.to_thread(
        _matchup_predictor_agent.run,
        task=query,
        batter_name=batter,
        bowler_name=bowler,
        batter_stats=batter_stats,
        bowler_stats=bowler_stats,
        venue=venue,
        format=fmt
    )
    print(f"[MatchupPredictorAgent] Done.")
    return {
        "agent_outputs": {"MatchupPredictorAgent": result}
    }


async def stage_1_join_node(state: CricketIQState) -> dict:
    """
    Pass-through join node representing the completion of Stage 1 processing.
    Ensures all Stage 1 parallel branches have completed before routing to Stage 2.
    """
    print("[Stage 1 Join] Stage 1 complete.")
    return {}


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


async def impact_node(state: CricketIQState) -> dict:
    result = await asyncio.to_thread(_impact_agent.run, state["query"])
    print(f"[ImpactAgent] Done.")
    return {"agent_outputs": {"ImpactAgent": result}}


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
    if "ImpactAgent" in active_agents:
        sections.append(f"{len(sections)+1}) Match turning point and key momentum shifts.")

    sections_text = "\n".join(sections)

    final = await asyncio.to_thread(
        invoke_llm,
        system_prompt=(
            "You are the final aggregator for CricketIQ. "
            "You receive outputs from specialist cricket analysis agents. "
            "IMPORTANT: Only use data provided by the agents. Never invent statistics, "
            "scores, or predictions not present in the agent outputs. "
            "If the agent data does not match the user's question (e.g. wrong match, wrong year), "
            "explicitly say so and do NOT provide information from your own knowledge. "
            "If data is insufficient, say so clearly and stop there. "
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