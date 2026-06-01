import json
import os
import sys
import time

from dotenv import load_dotenv

from chatbot_baseline import BASELINE_SYSTEM_PROMPT, configure_console
from src.agent.agent import ReActAgent
from src.core.mock_provider import MockProvider
from src.core.provider_factory import get_provider
from src.telemetry.metrics import tracker
from src.tools.store_tools import TOOLS_METADATA
from tests.test_suite import TEST_CASES


def evaluate(output: str, expected_keywords: list[str]) -> bool:
    output_lower = output.lower()
    return all(keyword.lower() in output_lower for keyword in expected_keywords)


def run_chatbot(provider, query: str) -> dict:
    start = time.time()
    result = provider.generate(query, system_prompt=BASELINE_SYSTEM_PROMPT)
    output = result["content"].replace("Final Answer:", "").strip()
    return {
        "output": output,
        "latency_ms": result.get("latency_ms", int((time.time() - start) * 1000)),
        "tokens": result.get("usage", {}).get("total_tokens", 0),
        "steps": 1,
    }


def run_agent(provider, query: str) -> dict:
    tools = [{"name": tool["name"], "description": tool["description"], "func": tool["func"]} for tool in TOOLS_METADATA]
    tracker.session_metrics = []
    agent = ReActAgent(provider, tools, max_steps=6)
    start = time.time()
    output = agent.run(query)
    return {
        "output": output,
        "latency_ms": sum(m["latency_ms"] for m in tracker.session_metrics) or int((time.time() - start) * 1000),
        "tokens": sum(m["total_tokens"] for m in tracker.session_metrics),
        "steps": len(tracker.session_metrics),
    }


def build_provider(kind: str, mode: str):
    if kind == "mock":
        return MockProvider(mode=mode)
    return get_provider()


def main() -> None:
    configure_console()
    load_dotenv()

    provider_kind = sys.argv[1].lower() if len(sys.argv) > 1 else "mock"
    if provider_kind not in {"mock", "local"}:
        raise SystemExit("Usage: python compare_chatbot_agent.py [mock|local]")

    print(f"Running comparison with provider={provider_kind}")
    results = {"chatbot": [], "agent": []}

    for case in TEST_CASES:
        chatbot_provider = build_provider(provider_kind, "chatbot")
        agent_provider = build_provider(provider_kind, "agent_v2")

        chatbot_result = run_chatbot(chatbot_provider, case["query"])
        agent_result = run_agent(agent_provider, case["query"])

        chatbot_pass = evaluate(chatbot_result["output"], case["expected_keywords"])
        agent_pass = evaluate(agent_result["output"], case["expected_keywords"])

        results["chatbot"].append({**case, **chatbot_result, "success": chatbot_pass})
        results["agent"].append({**case, **agent_result, "success": agent_pass})

        print(
            f"Case {case['id']}: {case['name']} | "
            f"chatbot={'PASS' if chatbot_pass else 'FAIL'} | "
            f"agent={'PASS' if agent_pass else 'FAIL'}"
        )

    os.makedirs("logs", exist_ok=True)
    output_path = os.path.join("logs", "baseline_vs_agent.json")
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    for mode, rows in results.items():
        passed = sum(1 for row in rows if row["success"])
        print(f"{mode}: {passed}/{len(rows)} passed")
    print(f"Saved detailed comparison to {output_path}")


if __name__ == "__main__":
    main()
