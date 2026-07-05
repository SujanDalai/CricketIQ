import asyncio
from src.config import Config
from src.graph.workflow import cricketiq_graph
from src.graph.state import CricketIQState


def main():
    print("Welcome to CricketIQ - Multi-Agent System (powered by LangGraph)")

    config = Config()
    print(f"Provider: {config.LLM_PROVIDER}")
    print(f"Model: {config.LLM_MODEL}")

    query = input("\nAsk CricketIQ: ")

    # Initial state passed into the graph
    initial_state: CricketIQState = {
        "query": query,
        "planned_agents": [],
        "agent_outputs": {},
        "final_report": "",
    }

    result = asyncio.run(cricketiq_graph.ainvoke(initial_state))
    print(result["final_report"])


if __name__ == "__main__":
    main()


