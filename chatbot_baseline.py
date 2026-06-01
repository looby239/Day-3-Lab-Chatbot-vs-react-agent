import os
import sys
import time

from dotenv import load_dotenv

from src.core.provider_factory import get_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


BASELINE_SYSTEM_PROMPT = """
You are a baseline retail/e-commerce chatbot.
Answer the user directly using only your model knowledge.
Do not call tools, do not invent tool observations, and do not use ReAct format.
If the question needs live store data such as exact stock, coupons, or shipping,
give your best direct answer and mention that it was not verified by tools.
"""


FAILURE_PROBES = [
    "Tôi muốn mua 2 iPhone 15, dùng mã WINNER, giao đến Hà Nội. Tổng tiền là bao nhiêu và còn hàng không?",
    "MacBook Air còn hàng không bạn? Tôi muốn mua 1 cái.",
    "Tôi muốn mua 1 iPad Pro, dùng mã giảm giá HELLO, giao đến Hồ Chí Minh. Tính tổng chi phí giúp tôi.",
    "Cửa hàng có bán máy giặt Toshiba không?",
    "So sánh giá và tồn kho của iPhone 15 và iPad Pro.",
]


def configure_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass


def ask_chatbot(provider, user_input: str) -> str:
    start = time.time()
    logger.log_event("CHATBOT_BASELINE_START", {"input": user_input, "model": provider.model_name})
    result = provider.generate(user_input, system_prompt=BASELINE_SYSTEM_PROMPT)
    content = result["content"].replace("Final Answer:", "").strip()
    latency_ms = result.get("latency_ms", int((time.time() - start) * 1000))
    usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    tracker.track_request(result.get("provider", os.getenv("DEFAULT_PROVIDER", "local")), provider.model_name, usage, latency_ms)
    logger.log_event("CHATBOT_BASELINE_END", {"success": True, "output": content})
    return content


def main() -> None:
    configure_console()
    load_dotenv()
    provider = get_provider()

    print("Chatbot baseline is ready.")
    print(f"Provider: {os.getenv('DEFAULT_PROVIDER', 'local')} | Model: {provider.model_name}")
    print("\nFailure probes to try:")
    for idx, probe in enumerate(FAILURE_PROBES, start=1):
        print(f"{idx}. {probe}")
    print("\nType your question, or type 'exit' to quit.\n")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        try:
            print("Assistant:", ask_chatbot(provider, user_input))
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
