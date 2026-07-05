"""
CricketIQ LangGraph workflow assembly.
"""

from langgraph.graph import StateGraph, END

from src.graph.state import CricketIQState
from src.graph.router import route_to_agents
from src.graph.nodes import (
    supervisor_node,
    cricket_node,
    bowler_node,
    matchup_node,
    weather_node,
    pitch_node,
    live_match_node,
    matchup_predictor_node,
    impact_node,
    aggregator_node,
)

_AGENT_NODES = [
    "cricket_node",
    "bowler_node",
    "matchup_node",
    "weather_node",
    "pitch_node",
    "live_match_node",
    "matchup_predictor_node",
    "impact_node",
]


def build_graph():
    builder = StateGraph(CricketIQState)

    builder.add_node("supervisor_node",        supervisor_node)
    builder.add_node("cricket_node",           cricket_node)
    builder.add_node("bowler_node",            bowler_node)
    builder.add_node("matchup_node",           matchup_node)
    builder.add_node("weather_node",           weather_node)
    builder.add_node("pitch_node",             pitch_node)
    builder.add_node("live_match_node",        live_match_node)
    builder.add_node("matchup_predictor_node", matchup_predictor_node)
    builder.add_node("impact_node",            impact_node)
    builder.add_node("aggregator_node",        aggregator_node)

    builder.set_entry_point("supervisor_node")

    builder.add_conditional_edges(
        "supervisor_node",
        route_to_agents,
        {node: node for node in _AGENT_NODES},
    )

    for node in _AGENT_NODES:
        builder.add_edge(node, "aggregator_node")

    builder.add_edge("aggregator_node", END)

    return builder.compile()


cricketiq_graph = build_graph()