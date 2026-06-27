import ollama

class OllamaClient:
    """
    Client for interacting with local Ollama service using the Qwen model.
    """
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model
        # Note: ollama client settings can be customized here if needed

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # TODO: Implement generation logic using ollama library
        pass
