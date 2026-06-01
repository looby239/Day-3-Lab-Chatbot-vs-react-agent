import os
from typing import Optional

from chatbot_baseline import ask_chatbot
from src.core.mock_provider import MockProvider
from src.core.provider_factory import get_provider
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


_provider: Optional[LLMProvider] = None
_provider_mode: Optional[str] = None


def _get_baseline_provider() -> LLMProvider:
    global _provider, _provider_mode
    provider_mode = os.getenv("UX_PROVIDER", "").strip().lower()
    if _provider is not None and _provider_mode == provider_mode:
        return _provider

    if provider_mode == "mock":
        _provider = MockProvider(mode="chatbot")
        _provider_mode = provider_mode
        return _provider

    try:
        _provider = get_provider()
        _provider_mode = provider_mode
        return _provider
    except Exception as exc:
        logger.log_event(
            "UX_PROVIDER_FALLBACK",
            {"mode": "chatbot", "reason": str(exc), "fallback": "MockProvider(chatbot)"},
        )
        _provider = MockProvider(mode="chatbot")
        _provider_mode = provider_mode
        return _provider


def answer_chatbot(question: str) -> str:
    """
    Adapter used by the Streamlit UX.

    It calls the merged chatbot baseline when a real provider is available,
    and falls back to the mock provider so the UI remains demoable.
    """
    return ask_chatbot(_get_baseline_provider(), question)
