import os
from src.config import Config
from functools import lru_cache
from langchain_groq import ChatGroq

@lru_cache(maxsize=1)
def get_llm():
    """
    Returns a shared ChatGroq LLM instance.
    lru_cache ensures we only create it once (singleton).
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")

    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=api_key,
        temperature=0.3,      # low = more factual, less creative
        max_tokens=1024,
    )


def invoke_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Helper to call the LLM with a system + user message.
    Returns the response as a plain string.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return response.content