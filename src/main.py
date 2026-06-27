from src.config import Config
from src.agents.coordinator import CoordinatorAgent


def main():
    print("Welcome to CricketIQ - Multi-Agent System")

    config = Config()
    print(f"Using model: {config.OLLAMA_MODEL}")

    coordinator = CoordinatorAgent()

    print(f"Coordinator initialized: {coordinator.name}")
    print(f"Role: {coordinator.role}")
    query = input("\nAsk CricketIQ: ")
    response = coordinator.run(query)
    print(response)

if __name__ == "__main__":
    main()