"""
Tests for the CricketIQ LangGraph workflow.

Covers:
- Supervisor routing decisions
- Individual agent node outputs
- Full end-to-end graph execution
- Router fan-out logic
"""

# pyrefly: ignore [missing-import]
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from src.graph.state import CricketIQState
from src.graph.router import route_to_agents, AGENT_TO_NODE
from src.graph.nodes import supervisor_node, cricket_node, pitch_node, aggregator_node
from src.graph.workflow import build_graph


# ---------------------------------------------------------------------------
# Helper: make a minimal state
# ---------------------------------------------------------------------------

def make_state(query: str = "", planned_agents=None, agent_outputs=None) -> CricketIQState:
    return {
        "query": query,
        "planned_agents": planned_agents or [],
        "agent_outputs": agent_outputs or {},
        "final_report": "",
    }


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestRouter:
    def test_maps_known_agents_to_nodes(self):
        state = make_state(planned_agents=["CricketAgent", "BowlerAgent", "PitchAgent"])
        result = route_to_agents(state)
        assert "cricket_node" in result
        assert "bowler_node" in result
        assert "pitch_node" in result

    def test_filters_unknown_agent_names(self):
        state = make_state(planned_agents=["CricketAgent", "NonExistentAgent"])
        result = route_to_agents(state)
        assert "cricket_node" in result
        assert len(result) == 1  # unknown filtered out

    def test_empty_planned_agents_falls_back_to_cricket(self):
        state = make_state(planned_agents=[])
        result = route_to_agents(state)
        assert result == ["cricket_node"]

    def test_all_agents_map_correctly(self):
        state = make_state(planned_agents=list(AGENT_TO_NODE.keys()))
        result = route_to_agents(state)
        assert set(result) == set(AGENT_TO_NODE.values())


# ---------------------------------------------------------------------------
# Supervisor node tests
# ---------------------------------------------------------------------------

class TestSupervisorNode:
    @patch("src.graph.nodes.ollama.chat")
    def test_supervisor_returns_planned_agents(self, mock_chat):
        mock_chat.return_value = {
            "message": {"content": '["CricketAgent", "BowlerAgent", "PitchAgent"]'}
        }
        state = make_state(query="Will Kohli score vs Starc at Perth?")
        result = asyncio.run(supervisor_node(state))

        assert "planned_agents" in result
        assert "CricketAgent" in result["planned_agents"]

    @patch("src.graph.nodes.ollama.chat")
    def test_supervisor_filters_invalid_agents(self, mock_chat):
        mock_chat.return_value = {
            "message": {"content": '["CricketAgent", "FakeAgent"]'}
        }
        state = make_state(query="test query")
        result = asyncio.run(supervisor_node(state))

        assert "FakeAgent" not in result["planned_agents"]
        assert "CricketAgent" in result["planned_agents"]

    @patch("src.graph.nodes.ollama.chat")
    def test_supervisor_handles_bad_json(self, mock_chat):
        mock_chat.return_value = {
            "message": {"content": "This is not JSON at all"}
        }
        state = make_state(query="test")
        result = asyncio.run(supervisor_node(state))

        # Falls back to CricketAgent
        assert result["planned_agents"] == ["CricketAgent"]


# ---------------------------------------------------------------------------
# Individual agent node tests
# ---------------------------------------------------------------------------

class TestAgentNodes:
    @patch("src.graph.nodes._cricket_agent")
    def test_cricket_node_writes_agent_output(self, mock_agent):
        mock_agent.run.return_value = "=== BATTING ANALYSIS: Virat Kohli ==="
        state = make_state(query="Kohli batting form")
        result = asyncio.run(cricket_node(state))

        assert "agent_outputs" in result
        assert "CricketAgent" in result["agent_outputs"]
        assert "Kohli" in result["agent_outputs"]["CricketAgent"] or \
               result["agent_outputs"]["CricketAgent"] != ""

    @patch("src.graph.nodes._pitch_agent")
    def test_pitch_node_writes_agent_output(self, mock_agent):
        mock_agent.run.return_value = "=== PITCH ANALYSIS: Perth ==="
        state = make_state(query="pitch at Perth")
        result = asyncio.run(pitch_node(state))

        assert "PitchAgent" in result["agent_outputs"]


# ---------------------------------------------------------------------------
# Aggregator node tests
# ---------------------------------------------------------------------------

class TestAggregatorNode:
    @patch("src.graph.nodes.ollama.chat")
    def test_aggregator_generates_final_report(self, mock_chat):
        mock_chat.return_value = {
            "message": {"content": "Final analysis: Kohli is in great form."}
        }
        state = make_state(
            query="Will Kohli score?",
            agent_outputs={
                "CricketAgent": "Batting report here.",
                "PitchAgent": "Pitch report here.",
            }
        )
        result = asyncio.run(aggregator_node(state))

        assert "final_report" in result
        assert "CRICKETIQ FINAL REPORT" in result["final_report"]

    def test_aggregator_handles_empty_outputs(self):
        state = make_state(query="test", agent_outputs={})
        result = asyncio.run(aggregator_node(state))
        assert "final_report" in result
        assert "No agent outputs" in result["final_report"]


# ---------------------------------------------------------------------------
# End-to-end graph test
# ---------------------------------------------------------------------------

class TestGraphEndToEnd:
    @patch("src.graph.nodes.ollama.chat")
    def test_full_graph_invocation(self, mock_chat):
        """
        Full graph smoke test: supervisor routes to cricket_node,
        which runs, then aggregator produces a final report.
        """
        # Mock all ollama.chat calls in sequence
        mock_chat.side_effect = [
            # 1. Supervisor call → only CricketAgent
            {"message": {"content": '["CricketAgent"]'}},
            # 2. CricketAgent internal LLM call
            {"message": {"content": "Kohli is in excellent form with momentum score 8.2/10."}},
            # 3. Aggregator call
            {"message": {"content": "Final report: Kohli will score big today."}},
        ]

        graph = build_graph()
        result = asyncio.run(graph.ainvoke({
            "query": "Will virat kohli score today?",
            "planned_agents": [],
            "agent_outputs": {},
            "final_report": "",
        }))

        assert "final_report" in result
        assert result["final_report"].strip() != ""
        assert "CRICKETIQ FINAL REPORT" in result["final_report"]
