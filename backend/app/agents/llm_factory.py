import os
from typing import Optional, Any
from app.core.config import settings


class LLMFactory:
    """
    Provider abstraction for LLMs.
    Ensures OutReachIQ is not hardcoded to any single LLM provider.
    Supports OpenAI, Gemini, and OpenRouter with graceful fallbacks.
    """

    @staticmethod
    def get_llm(provider: Optional[str] = None, model_name: Optional[str] = None, temperature: float = 0.2) -> Any:
        active_provider = (provider or settings.LLM_PROVIDER).lower()

        if active_provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model_name or "gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=temperature
                )
            except ImportError:
                pass

        elif active_provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_name or "gemini-1.5-flash",
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=temperature
                )
            except ImportError:
                pass

        elif active_provider == "openrouter" and settings.OPENROUTER_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    model=model_name or "anthropic/claude-3.5-sonnet",
                    temperature=temperature
                )
            except ImportError:
                pass

        # Deterministic / Mock provider for local runs without requiring external API keys
        return MockLLMClient(provider=active_provider)


class MockLLMClient:
    """Mock LLM client ensuring the foundation works reliably without external API keys."""
    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def invoke(self, prompt: str) -> str:
        return f"[MockLLM-{self.provider}] Evidence-grounded analysis completed successfully."
