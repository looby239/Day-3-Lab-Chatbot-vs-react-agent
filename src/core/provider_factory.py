import os

from dotenv import load_dotenv

from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider


def get_provider() -> LLMProvider:
    """
    Build the configured LLM provider from environment variables.

    DEFAULT_PROVIDER options:
    - local: Phi-3 or another GGUF model through llama-cpp-python.
    - openai: OpenAI chat completion provider.
    - google: Gemini provider.
    """
    load_dotenv()

    provider = os.getenv("DEFAULT_PROVIDER", "local").strip().lower()
    model_name = os.getenv("DEFAULT_MODEL")

    if provider == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)

    if provider == "openai":
        return OpenAIProvider(
            model_name=model_name or "gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider in {"google", "gemini"}:
        return GeminiProvider(
            model_name=model_name or "gemini-1.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    raise ValueError(
        "Unsupported DEFAULT_PROVIDER. Expected one of: local, openai, google, gemini."
    )
