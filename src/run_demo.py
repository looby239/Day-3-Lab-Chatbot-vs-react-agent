import os
import re
import json
from typing import Any, Dict, List, Optional

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.core.mock_provider import MockProvider
from src.core.provider_factory import get_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.retail_tools import TOOLS_METADATA, search_product, check_stock, get_discount, calc_shipping


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
    if os.getenv("UX_PROVIDER", "").strip().lower() == "data":
        return _run_data_demo(question, version)

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


def _json_loads(payload: str) -> Dict[str, Any]:
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {"value": value}
    except Exception:
        return {"raw": payload}


def _run_data_demo(question: str, version: str = "v2") -> Dict[str, Any]:
    normalized = question.lower()
    product_query = "iPhone 15"
    quantity = 2 if re.search(r"\b2\b|hai", normalized) else 1
    coupon = "WINNER" if "winner" in normalized else "WELCOME" if "welcome" in normalized else ""
    destination = "Hanoi" if any(city in normalized for city in ["ha noi", "hanoi", "hà nội"]) else "Ho Chi Minh City"

    trace: List[Dict[str, Any]] = []

    search_raw = search_product(product_query)
    search_data = _json_loads(search_raw)
    products = search_data.get("products", [])
    selected = _select_product(products, product_query)
    trace.append(
        {
            "step": 1,
            "event": "TOOL_CALL",
            "thought": "Tim san pham trong src/data/products.json.",
            "action": "search_product",
            "tool_input": {"product_name": product_query},
            "observation": search_raw,
        }
    )

    if not selected:
        return {
            "answer": f"Khong tim thay san pham phu hop voi '{product_query}' trong data.",
            "trace": trace,
            "provider": "data-demo",
            "version": version,
        }

    stock_raw = check_stock(selected["id"], quantity)
    stock_data = _json_loads(stock_raw)
    trace.append(
        {
            "step": 2,
            "event": "TOOL_CALL",
            "thought": "Kiem tra ton kho bang product_id lay tu data.",
            "action": "check_stock",
            "tool_input": {"product_id": selected["id"], "quantity": quantity},
            "observation": stock_raw,
        }
    )

    subtotal = selected["price"] * quantity
    discount_amount = 0
    discount_note = "Khong dung ma giam gia."
    if coupon:
        discount_raw = get_discount(coupon, subtotal)
        discount_data = _json_loads(discount_raw)
        discount_amount = int(discount_data.get("discount_amount", 0)) if discount_data.get("valid") else 0
        discount_note = (
            f"Ma {coupon} hop le, giam {discount_amount:,} VND."
            if discount_data.get("valid")
            else f"Ma {coupon} khong ap dung: {discount_data.get('message', 'khong hop le')}."
        )
        trace.append(
            {
                "step": 3,
                "event": "TOOL_CALL",
                "thought": "Ap ma giam gia tu src/data/coupons.json.",
                "action": "get_discount",
                "tool_input": {"coupon_code": coupon, "order_value": subtotal},
                "observation": discount_raw,
            }
        )

    total_weight = selected["weight_kg"] * quantity
    shipping_raw = calc_shipping(total_weight, destination)
    shipping_data = _json_loads(shipping_raw)
    shipping_fee = int(shipping_data.get("shipping_fee", 0))
    trace.append(
        {
            "step": len(trace) + 1,
            "event": "TOOL_CALL",
            "thought": "Tinh phi giao hang tu src/data/shipping_rules.json.",
            "action": "calc_shipping",
            "tool_input": {"weight_kg": total_weight, "destination": destination},
            "observation": shipping_raw,
        }
    )

    final_total = subtotal - discount_amount + shipping_fee
    availability = (
        f"con hang, kho co {stock_data.get('available')} san pham"
        if stock_data.get("in_stock")
        else f"khong du hang, kho chi co {stock_data.get('available')} san pham"
    )
    answer = (
        f"Theo data trong src/data: {selected['name']} {availability}. "
        f"Tam tinh {quantity} san pham: {subtotal:,} VND. "
        f"{discount_note} Phi ship den {destination}: {shipping_fee:,} VND. "
        f"Tong thanh toan: {final_total:,} VND."
    )

    trace.append(
        {
            "step": len(trace) + 1,
            "event": "FINAL_ANSWER",
            "thought": "Tong hop ket qua tu cac tool doc JSON data.",
            "action": "return_answer",
            "tool_input": {},
            "observation": answer,
        }
    )

    return {"answer": answer, "trace": trace, "provider": "data-demo", "version": version}


def _select_product(products: List[Dict[str, Any]], product_query: str) -> Optional[Dict[str, Any]]:
    if not products:
        return None

    query = product_query.lower()
    for product in products:
        if product.get("name", "").lower() == query:
            return product
    for product in products:
        name = product.get("name", "").lower()
        if query in name and "pro" not in name and "max" not in name:
            return product
    return products[0]
