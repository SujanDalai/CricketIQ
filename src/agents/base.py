from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Abstract base class representing an Agent in the multi-agent system.
    """
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def run(self, task: str) -> str:
        """
        Execute the agent's main logic for a given task.
        """
        pass
