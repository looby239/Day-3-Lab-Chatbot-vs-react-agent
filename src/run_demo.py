import os
import re
from typing import Any, Dict, List, Optional

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.core.mock_provider import MockProvider
from src.core.provider_factory import get_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.store_tools import TOOLS_METADATA


_providers: Dict[str, LLMProvider] = {}


def _build_provider(version: str) -> LLMProvider:
    provider_mode = os.getenv("UX_PROVIDER", "").strip().lower()
    cache_key = f"{provider_mode or 'env'}:{version}"
    if cache_key in _providers:
        return _providers[cache_key]

    if provider_mode == "mock":
        provider = MockProvider(mode=_mock_mode(version))
        _providers[cache_key] = provider
        return provider

    try:
        provider = get_provider()
        _providers[cache_key] = provider
        return provider
    except Exception as exc:
        logger.log_event(
            "UX_PROVIDER_FALLBACK",
            {"mode": f"agent_{version}", "reason": str(exc), "fallback": "MockProvider"},
        )
        provider = MockProvider(mode=_mock_mode(version))
        _providers[cache_key] = provider
        return provider


def _mock_mode(version: str) -> str:
    return "agent_v2" if version == "v2" else "agent_v1"


def _build_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "func": tool["func"],
        }
        for tool in TOOLS_METADATA
    ]


def _extract_first(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def _trace_from_history(history: List[str]) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    step = 1

    for idx, entry in enumerate(history):
        if entry.startswith("User:") or entry.startswith("Observation:"):
            continue

        thought = _extract_first(r"Thought:\s*(.*?)(?:\nAction:|\nFinal Answer:|$)", entry)
        action = _extract_first(r"Action:\s*([a-zA-Z_]\w*\s*\(.*?\))", entry)

        observation = ""
        if idx + 1 < len(history) and history[idx + 1].startswith("Observation:"):
            observation = history[idx + 1].replace("Observation:", "", 1).strip()

        if thought or action or observation:
            trace.append(
                {
                    "step": step,
                    "event": "TOOL_CALL" if action else "AGENT_STEP",
                    "thought": thought or "",
                    "action": action or "",
                    "tool_input": _tool_input_from_action(action),
                    "observation": observation,
                }
            )
            step += 1

    return trace


def _tool_input_from_action(action: Optional[str]) -> Dict[str, Any]:
    if not action:
        return {}

    match = re.search(r"^([a-zA-Z_]\w*)\s*\((.*)\)$", action.strip(), re.DOTALL)
    if not match:
        return {"raw_action": action}

    return {
        "tool": match.group(1),
        "args": match.group(2).strip(),
    }


def run_agent(question: str, version: str = "v1") -> Dict[str, Any]:
    """
    Adapter used by the Streamlit UX.

    Returns the shape expected by src/app.py:
    {
        "answer": "...",
        "trace": [...]
    }
    """
    normalized_version = "v2" if str(version).lower() == "v2" else "v1"
    provider = _build_provider(normalized_version)
    tools = _build_tools()
    tracker.session_metrics = []

    max_steps = 6 if normalized_version == "v2" else 5
    agent = ReActAgent(provider, tools, max_steps=max_steps)
    answer = agent.run(question)
    trace = _trace_from_history(agent.history)

    for item in trace:
        logger.log_event(
            item.get("event", "AGENT_STEP"),
            {
                "step": item.get("step"),
                "thought": item.get("thought"),
                "action": item.get("action"),
                "tool_input": item.get("tool_input"),
                "observation": item.get("observation"),
            },
        )

    if not trace and tracker.session_metrics:
        trace = [
            {
                "step": 1,
                "event": "LLM_METRIC",
                "thought": "Agent completed without exposing step history.",
                "action": "provider.generate",
                "tool_input": {},
                "observation": f"{len(tracker.session_metrics)} model call(s) recorded.",
            }
        ]

    trace.append(
        {
            "step": len(trace) + 1,
            "event": "FINAL_ANSWER",
            "thought": "Agent returned a final answer to the user.",
            "action": "return_answer",
            "tool_input": {},
            "observation": answer,
        }
    )

    return {
        "answer": answer,
        "trace": trace,
        "metrics": tracker.session_metrics,
        "provider": provider.model_name,
        "version": normalized_version,
    }
