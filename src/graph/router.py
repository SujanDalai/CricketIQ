"""
Conditional edge functions for the CricketIQ LangGraph workflow.

After the supervisor_node writes 'planned_agents' to state, LangGraph
calls the router to decide which node(s) to visit next. The router
returns a list of node names — LangGraph fans out to all of them
(parallel execution) before converging on the aggregator.
"""

from src.graph.state import CricketIQState

# Map agent names (as returned by supervisor) to graph node names
AGENT_TO_NODE: dict[str, str] = {
    "CricketAgent":   "cricket_node",
    "BowlerAgent":    "bowler_node",
    "MatchupAgent":   "matchup_node",
    "WeatherAgent":   "weather_node",
    "PitchAgent":     "pitch_node",
    "LiveMatchAgent": "live_match_node",
}


def route_to_agents(state: CricketIQState) -> list[str]:
    """
    Reads 'planned_agents' from state and returns the corresponding
    list of graph node names for LangGraph to fan out to.

    Falls back to ['cricket_node'] if nothing was planned.
    """
    planned = state.get("planned_agents", [])

    nodes = [
        AGENT_TO_NODE[agent]
        for agent in planned
        if agent in AGENT_TO_NODE
    ]

    if not nodes:
        nodes = ["cricket_node"]

    return nodes
