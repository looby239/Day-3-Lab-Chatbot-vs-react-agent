import time
import os
import platform
import sys
from typing import Dict, Any, Optional, Generator
from llama_cpp import Llama
from src.core.llm_provider import LLMProvider

class LocalProvider(LLMProvider):
    """
    LLM Provider for local models using llama-cpp-python.
    Optimized for CPU usage with GGUF models.
    """
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize the local Llama model.
        Args:
            model_path: Path to the .gguf model file.
            n_ctx: Context window size.
            n_threads: Number of CPU threads to use. Defaults to all available.
        """
        super().__init__(model_name=os.path.basename(model_path))
        self.max_tokens = max_tokens or int(os.getenv("LOCAL_MAX_TOKENS", "256"))

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Please download it first.")

        try:
            # n_threads=None lets llama.cpp pick a reasonable CPU thread count.
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=0,
                verbose=False,
            )
        except OSError as exc:
            detail = (
                "llama-cpp-python failed while initializing the native llama.cpp backend. "
                f"Original error: {exc}. "
                f"Python: {sys.version.split()[0]}, OS: {platform.platform()}. "
                "On Windows, use the pinned CPU wheel: "
                "python -m pip install --force-reinstall --no-cache-dir --only-binary=:all: "
                "llama-cpp-python==0.2.90 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu"
            )
            raise RuntimeError(detail) from exc

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        response = self.llm(
            self._format_prompt(prompt, system_prompt),
            max_tokens=self.max_tokens,
            stop=["<|end|>", "Observation:"],
            echo=False,
            temperature=0.2,
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        content = response["choices"][0]["text"].strip()
        usage = {
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
            "total_tokens": response["usage"]["total_tokens"]
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "local"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        stream = self.llm(
            self._format_prompt(prompt, system_prompt),
            max_tokens=self.max_tokens,
            stop=["<|end|>", "Observation:"],
            stream=True,
            temperature=0.2,
        )

        for chunk in stream:
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    def _format_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if system_prompt:
            return f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>"
        return f"<|user|>\n{prompt}<|end|>\n<|assistant|>"
