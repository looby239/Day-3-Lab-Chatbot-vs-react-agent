import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

LOG_DIR = ROOT_DIR / "logs"
SCENARIOS = {
    "Tư vấn sản phẩm": "Toi can mua mot dien thoai de chup anh dep, goi y san pham phu hop.",
    "Kiểm tra tồn kho": "iPhone 15 con hang khong? Toi can mua 2 cai.",
    "Áp mã giảm giá": "Toi mua 2 iPhone 15 dung ma WINNER thi duoc giam bao nhieu?",
    "Tính tổng đơn hàng": "Toi muon mua 2 iPhone 15, dung ma WINNER, giao den Ha Noi. Tong tien la bao nhieu va con hang khong?",
}


def _thinking_message(mode: str) -> str:
    if mode == "Chatbot Baseline":
        return "Chatbot dang tao cau tra loi..."
    return "Agent dang suy nghi va goi tools..."


def _error_trace(message: str) -> List[Dict[str, Any]]:
    return [
        {
            "step": "error",
            "event": "UX_ERROR",
            "thought": "The UI caught an execution problem before a valid answer was returned.",
            "action": "handle_error",
            "tool_input": {},
            "observation": message,
        }
    ]


def _init_session() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_trace", [])
    st.session_state.setdefault("last_error", None)
    st.session_state.setdefault("draft_question", SCENARIOS["Tính tổng đơn hàng"])


def _mock_trace(question: str, mode: str) -> Dict[str, Any]:
    if mode == "Chatbot Baseline":
        return {
            "answer": (
                "Day la cau tra loi baseline tam thoi. Khi src/chatbot.py san sang, "
                "UI se goi model Phi-3 truc tiep de so sanh voi Agent."
            ),
            "trace": [
                {
                    "step": 1,
                    "event": "BASELINE_RESPONSE",
                    "thought": "Baseline khong su dung tool.",
                    "action": "llm_generate",
                    "tool_input": {"question": question},
                    "observation": "No tool observation.",
                }
            ],
        }

    return {
        "answer": (
            "Demo tam thoi: iPhone 15 con hang, mua 2 san pham dung ma WINNER "
            "duoc giam 10%, phi ship Ha Noi la 30,000 VND. Khi Agent that duoc "
            "merge, ket qua nay se lay tu tool calls."
        ),
        "trace": [
            {
                "step": 1,
                "event": "TOOL_CALL",
                "thought": "Can tim thong tin san pham truoc.",
                "action": "search_product",
                "tool_input": {"product_name": "iPhone 15"},
                "observation": "Found iPhone 15, price 22000000, stock 5, weight 0.3kg.",
            },
            {
                "step": 2,
                "event": "TOOL_CALL",
                "thought": "Can kiem tra so luong ton kho.",
                "action": "check_stock",
                "tool_input": {"product_id": "iphone15", "quantity": 2},
                "observation": "In stock. Available quantity: 5.",
            },
            {
                "step": 3,
                "event": "TOOL_CALL",
                "thought": "Can ap ma giam gia.",
                "action": "get_discount",
                "tool_input": {"coupon_code": "WINNER", "order_value": 44000000},
                "observation": "Coupon valid. Discount: 10%.",
            },
            {
                "step": 4,
                "event": "TOOL_CALL",
                "thought": "Can tinh phi ship den Ha Noi.",
                "action": "calc_shipping",
                "tool_input": {"weight_kg": 0.6, "destination": "Ha Noi"},
                "observation": "Shipping fee: 30000 VND.",
            },
        ],
    }


def _try_real_baseline(question: str) -> Optional[Dict[str, Any]]:
    try:
        from src.chatbot import answer_chatbot
    except Exception:
        return None

    answer = answer_chatbot(question)
    return {
        "answer": str(answer),
        "trace": [
            {
                "step": 1,
                "event": "BASELINE_RESPONSE",
                "thought": "Called src.chatbot.answer_chatbot.",
                "action": "answer_chatbot",
                "tool_input": {"question": question},
                "observation": str(answer),
            }
        ],
    }


def _try_real_agent(question: str, version: str) -> Optional[Dict[str, Any]]:
    try:
        from src.run_demo import run_agent
    except Exception:
        return None

    result = run_agent(question, version=version)
    if isinstance(result, dict):
        return {
            "answer": str(result.get("answer", "")),
            "trace": result.get("trace", []),
        }
    return {"answer": str(result), "trace": []}


def run_question(question: str, mode: str) -> Dict[str, Any]:
    if mode == "Chatbot Baseline":
        result = _try_real_baseline(question)
    else:
        version = "v2" if mode == "ReAct Agent v2" else "v1"
        result = _try_real_agent(question, version)

    if result:
        return result
    return _mock_trace(question, mode)


def _normalize_result(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Backend did not return a result dictionary.")

    answer = str(result.get("answer", "")).strip()
    trace = result.get("trace", [])

    if not answer:
        raise ValueError("Backend returned an empty answer.")
    if trace is None:
        trace = []
    if not isinstance(trace, list):
        trace = [
            {
                "step": 1,
                "event": "TRACE_PARSE_WARNING",
                "thought": "Trace was returned in a non-list format.",
                "action": "normalize_trace",
                "tool_input": {},
                "observation": str(trace),
            }
        ]

    return {"answer": answer, "trace": trace}


def _read_json_logs(limit: int = 80) -> List[Dict[str, Any]]:
    if not LOG_DIR.exists():
        return []

    log_files = sorted(LOG_DIR.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    events: List[Dict[str, Any]] = []
    for log_file in log_files[:3]:
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload["_file"] = log_file.name
            events.append(payload)

    return events[-limit:]


def _render_trace(trace: List[Dict[str, Any]]) -> None:
    if not trace:
        st.info("Chua co trace truc tiep. Hay chay mot cau hoi hoac xem log file ben duoi.")
        return

    for item in trace:
        step = item.get("step", "-")
        event = item.get("event", "AGENT_STEP")
        with st.expander(f"Step {step} - {event}", expanded=True):
            if item.get("thought"):
                st.markdown("**Thought**")
                st.write(item["thought"])
            if item.get("action"):
                st.markdown("**Action**")
                st.code(str(item["action"]), language="text")
            if item.get("tool_input") is not None:
                st.markdown("**Tool input**")
                st.json(item["tool_input"])
            if item.get("observation"):
                st.markdown("**Observation**")
                st.write(item["observation"])


def _render_log_file_events() -> None:
    events = _read_json_logs()
    if not events:
        st.info("Chua tim thay log JSON trong thu muc logs/.")
        return

    for event in reversed(events[-30:]):
        event_name = event.get("event", "UNKNOWN")
        timestamp = event.get("timestamp", "")
        source = event.get("_file", "")
        with st.expander(f"{event_name} | {timestamp} | {source}"):
            st.json(event.get("data", event))


def _submit_question(question: str, mode: str) -> None:
    clean_question = question.strip()
    if not clean_question:
        return

    st.session_state.messages.append({"role": "user", "content": clean_question})
    started_at = datetime.now()
    status = st.status(_thinking_message(mode), expanded=True)
    status.write("Nhan cau hoi va chuan bi context.")
    if mode != "Chatbot Baseline":
        status.write("Dang cho Agent sinh Thought/Action va thuc thi tool neu can.")

    try:
        result = _normalize_result(run_question(clean_question, mode))
        elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        status.write("Da nhan ket qua va cap nhat trace.")
        status.update(label="Hoan tat", state="complete", expanded=False)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "mode": mode,
                "latency_ms": elapsed_ms,
            }
        )
        st.session_state.last_trace = result["trace"]
        st.session_state.last_error = None
    except Exception as exc:
        elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        error_message = str(exc)
        status.write("Khong nhan duoc ket qua hop le tu backend.")
        status.update(label="Gap loi khi xu ly", state="error", expanded=True)

        st.session_state.last_error = error_message
        st.session_state.last_trace = _error_trace(error_message)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Minh chua lay duoc ket qua hop le tu backend. "
                    f"Chi tiet loi: {error_message}"
                ),
                "mode": mode,
                "latency_ms": elapsed_ms,
            }
        )


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    _init_session()

    st.set_page_config(page_title="Lab 3 Retail Agent Demo", page_icon="LOG", layout="wide")
    st.title("Lab 3 Retail Agent Demo")

    with st.sidebar:
        st.subheader("Mode")
        mode = st.radio(
            "Chon cach tra loi",
            ["Chatbot Baseline", "ReAct Agent v1", "ReAct Agent v2"],
            label_visibility="collapsed",
        )

        st.subheader("Scenario")
        for label, prompt in SCENARIOS.items():
            if st.button(label, use_container_width=True):
                st.session_state.draft_question = prompt

        st.divider()
        if st.button("Reset conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_trace = []
            st.session_state.last_error = None

        st.caption(f"Log dir: {LOG_DIR}")

    chat_col, log_col = st.columns([0.58, 0.42], gap="large")

    with chat_col:
        st.subheader("Chat")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message["role"] == "assistant" and message.get("latency_ms") is not None:
                    st.caption(f"{message.get('mode')} | {message['latency_ms']} ms")

        question = st.chat_input("Nhập câu hỏi...")
        if question:
            _submit_question(question, mode)
            st.rerun()

        with st.form("scenario_form"):
            draft = st.text_area("Cau hoi demo", value=st.session_state.draft_question, height=90)
            submitted = st.form_submit_button("Gui cau hoi")
            if submitted:
                st.session_state.draft_question = draft
                _submit_question(draft, mode)
                st.rerun()

    with log_col:
        st.subheader("Trace & Logs")
        if st.session_state.last_error:
            st.error(st.session_state.last_error)

        tab_trace, tab_logs = st.tabs(["Trace hien tai", "Log file"])
        with tab_trace:
            _render_trace(st.session_state.last_trace)
        with tab_logs:
            _render_log_file_events()


if __name__ == "__main__":
    main()
