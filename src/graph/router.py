"""
Conditional edge functions for the CricketIQ LangGraph workflow.
"""

from src.graph.state import CricketIQState

AGENT_TO_NODE: dict[str, str] = {
    "CricketAgent":          "cricket_node",
    "BowlerAgent":           "bowler_node",
    "MatchupAgent":          "matchup_node",
    "WeatherAgent":          "weather_node",
    "PitchAgent":            "pitch_node",
    "LiveMatchAgent":        "live_match_node",
    "MatchupPredictorAgent": "matchup_predictor_node",
    "ImpactAgent":           "impact_node",
    "HistoricalMatchAgent": "historical_match_node",
}


def route_to_agents(state: CricketIQState) -> list[str]:
    """
    Reads 'planned_agents' from state and returns the corresponding
    list of graph node names for LangGraph to fan out to.
    Falls back to live_match_node if nothing was planned.
    """
    planned = state.get("planned_agents", [])

    nodes = [
        AGENT_TO_NODE[agent]
        for agent in planned
        if agent in AGENT_TO_NODE
    ]

    if not nodes:
        nodes = ["live_match_node"]

    return nodes