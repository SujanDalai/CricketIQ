from src.config import Config
from src.graph.workflow import cricketiq_graph
from src.graph.state import CricketIQState


def main():
    print("Welcome to CricketIQ - Multi-Agent System (powered by LangGraph)")

    config = Config()
    print(f"Using model: {config.OLLAMA_MODEL}")

    query = input("\nAsk CricketIQ: ")

    # Initial state passed into the graph
    initial_state: CricketIQState = {
        "query": query,
        "planned_agents": [],
        "agent_outputs": {},
        "final_report": "",
    }

    result = cricketiq_graph.invoke(initial_state)
    print(result["final_report"])


if __name__ == "__main__":
    main()