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

    Fields
    ------
    query : str
        The original user question, unchanged throughout the graph.
    planned_agents : list[str]
        The list of agent names chosen by the supervisor node.
        e.g. ["CricketAgent", "BowlerAgent", "WeatherAgent", "PitchAgent"]
    agent_outputs : dict[str, str]
        A mapping of agent_name → the text output that agent produced.
        Uses operator.or_ so each node can merge its result without
        overwriting other agents' outputs.
    final_report : str
    vs_batter_hint: str
    vs_bowler_hint: str
        The finished CricketIQ report, written by the aggregator node.
    """
    query: str
    planned_agents: list[str]
    agent_outputs: Annotated[dict[str, str], operator.or_]
    final_report: str
