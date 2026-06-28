"""
CricketIQ LangGraph workflow assembly.

This module builds and compiles the StateGraph that powers CricketIQ.
It wires together:
  supervisor_node → (conditional fan-out) → agent nodes → aggregator_node

Usage
-----
    from src.graph.workflow import build_graph

    graph = build_graph()
    result = graph.invoke({
        "query": "Will Kohli score vs Starc at Perth in Test?",
        "planned_agents": [],
        "agent_outputs": {},
        "final_report": "",
    })
    print(result["final_report"])
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
    aggregator_node,
)

# All specialist agent node names (must match what route_to_agents returns)
_AGENT_NODES = [
    "cricket_node",
    "bowler_node",
    "matchup_node",
    "weather_node",
    "pitch_node",
    "live_match_node",
    "matchup_predictor_node",
]


def build_graph():
    """
    Assembles and compiles the CricketIQ LangGraph StateGraph.

    Graph topology
    --------------
    START
      └─► supervisor_node
            └─► [conditional fan-out via route_to_agents]
                  ├─► cricket_node ──┐
                  ├─► bowler_node ───┤
                  ├─► matchup_node ──┤
                  ├─► weather_node ──┼─► aggregator_node ─► END
                  ├─► pitch_node ────┤
                  └─► live_match_node┘

    Returns
    -------
    CompiledGraph
        A compiled LangGraph graph ready for .invoke() / .stream() calls.
    """
    builder = StateGraph(CricketIQState)

    # --- Add nodes ---
    builder.add_node("supervisor_node",  supervisor_node)
    builder.add_node("cricket_node",     cricket_node)
    builder.add_node("bowler_node",      bowler_node)
    builder.add_node("matchup_node",     matchup_node)
    builder.add_node("weather_node",     weather_node)
    builder.add_node("pitch_node",       pitch_node)
    builder.add_node("live_match_node",  live_match_node)
    builder.add_node("matchup_predictor_node", matchup_predictor_node)
    builder.add_node("aggregator_node",  aggregator_node)

    # --- Entry point ---
    builder.set_entry_point("supervisor_node")

    # --- Conditional fan-out: supervisor → agent nodes ---
    builder.add_conditional_edges(
        "supervisor_node",
        route_to_agents,
        {node: node for node in _AGENT_NODES},
    )

    # --- Each agent node flows into the aggregator ---
    for node in _AGENT_NODES:
        builder.add_edge(node, "aggregator_node")

    # --- Aggregator is the terminal node ---
    builder.add_edge("aggregator_node", END)

    return builder.compile()


# Module-level compiled graph (singleton — import and reuse)
cricketiq_graph = build_graph()
