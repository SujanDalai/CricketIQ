"""
Shared state schema for the CricketIQ LangGraph workflow.

Every node in the graph receives and returns a CricketIQState dict.
LangGraph merges return values back into the running state automatically.
"""

from typing import Annotated
from typing_extensions import TypedDict
import operator


class CricketIQState(TypedDict):
    """
    The single shared state object that flows through every node
    in the CricketIQ LangGraph workflow.
    """
    query: str
    planned_agents: list[str]
    agent_outputs: Annotated[dict[str, str], operator.or_]
    final_report: str
    vs_batter_hint: str
    vs_bowler_hint: str
    venue: str
    format: str
    batter_name: str
    bowler_name: str
    batter_stats: dict
    bowler_stats: dict