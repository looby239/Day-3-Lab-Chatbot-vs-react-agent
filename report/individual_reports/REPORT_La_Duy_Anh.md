# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: La_Duy_Anh
- **Student ID**: [Update student ID]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### Role

I was responsible for **Person 4: UX Demo + Log Viewer**. My main objective was to make the chatbot/agent system demoable through a web UI and make the ReAct reasoning trace visible to users and instructors.

### Modules Implemented

- `src/app.py`
  - Built the Streamlit web application for the retail assistant demo.
  - Added mode selection for `Chatbot Baseline`, `ReAct Agent v1`, and `ReAct Agent v2`.
  - Added quick scenario buttons for product advice, stock checking, coupon application, and full order calculation.
  - Added chat history rendering with latency display.
  - Added a live trace panel showing `Thought`, `Action`, `Tool input`, and `Observation`.
  - Added a log viewer that reads JSON events from `logs/*.log`.
  - Added user-facing thinking states while the chatbot/agent is running.
  - Added error handling for empty answers, invalid backend results, malformed trace data, and execution errors.

- `src/chatbot.py`
  - Added a thin adapter exposing `answer_chatbot(question: str) -> str`.
  - Connected the UX to the merged baseline chatbot implementation in `chatbot_baseline.py`.
  - Added fallback to `MockProvider(mode="chatbot")` when the local Phi-3 model is not available.

- `src/run_demo.py`
  - Added a thin adapter exposing `run_agent(question: str, version: str = "v1") -> dict`.
  - Connected the UX to `ReActAgent` and the retail tools.
  - Converted agent history into a UI-friendly trace format.
  - Logged `TOOL_CALL` events so the log viewer can display tool execution details.
  - Added fallback to `MockProvider(mode="agent_v1" | "agent_v2")` when the local Phi-3 model is not available.

- `requirements.txt`
  - Added `streamlit>=1.35.0`.

### Code Highlights

The UI expects a stable result contract:

```python
{
    "answer": "...",
    "trace": [
        {
            "step": 1,
            "event": "TOOL_CALL",
            "thought": "...",
            "action": "...",
            "tool_input": {...},
            "observation": "..."
        }
    ]
}
```

This made the UX independent from the internal agent implementation. The agent team can improve parsing, prompts, and tools without changing the UI as long as this contract remains stable.

### Documentation

The UX connects the system as follows:

```text
User -> Streamlit UI -> src/chatbot.py or src/run_demo.py
                       -> ReActAgent
                       -> Retail tools
                       -> JSON logs
                       -> Trace & Log Viewer
```

The UI is not only a chat window. It is also an observability tool for the lab because it exposes the internal ReAct loop in a readable way.

---

## II. Debugging Case Study (10 Points)

### Problem Description

After the UX was connected to the backend, the system could fail when the Phi-3 model file was not available locally:

```text
Model file not found at ./models/Phi-3-mini-4k-instruct-q4.gguf
```

Without handling this case, the web demo would fail before users could compare chatbot vs agent behavior.

### Log Source

Example event from `logs/2026-06-01.log`:

```json
{
  "event": "UX_PROVIDER_FALLBACK",
  "data": {
    "mode": "agent_v2",
    "reason": "Model file not found at ./models/Phi-3-mini-4k-instruct-q4.gguf. Please download it first.",
    "fallback": "MockProvider"
  }
}
```

The logs also showed the successful ReAct trace after fallback:

```json
{
  "event": "TOOL_CALL",
  "data": {
    "step": 1,
    "action": "search_product(product_name=\"iPhone 15\")",
    "observation": "{\"status\": \"success\", \"products\": [...]}"
  }
}
```

### Diagnosis

The issue was not in the UX itself. The local provider correctly required the GGUF model file, but the demo environment did not always have Phi-3 downloaded. This created a reliability risk for live presentation.

Another UX risk was that agent backends can return unexpected shapes, such as:

- empty answer
- `None` trace
- trace not formatted as a list
- backend exception before answer generation

### Solution

I added defensive UX handling:

- `src/chatbot.py` and `src/run_demo.py` fall back to `MockProvider` when the real provider cannot load.
- `src/app.py` validates backend result shape through `_normalize_result`.
- If the answer is empty, the UI shows a clear error instead of silently failing.
- If trace is malformed, the UI converts it into a warning trace.
- If execution fails, the UI creates a `UX_ERROR` trace so the failure is visible in the demo.
- Added `st.status(...)` to show when the chatbot or agent is thinking.

This made the web demo robust enough to run even before the local Phi-3 setup is complete.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**

The chatbot baseline answers directly, so it often sounds confident even when it does not verify product price, stock, coupon validity, or shipping fee. The ReAct agent separates reasoning into `Thought`, `Action`, and `Observation`, which makes each decision auditable.

2. **Reliability**

The agent can be worse than a chatbot when the model outputs an invalid action format, calls a non-existent tool, or loops without producing `Final Answer`. This is why the UX needs error states, trace display, and max-step visibility. A beautiful answer is less useful if we cannot inspect how it was produced.

3. **Observation**

Observations are the key difference. After each tool call, the agent receives factual feedback from the store tools. For example, it can search `iPhone 15`, check stock, calculate shipping, and apply `WINNER`. This prevents the system from guessing and gives the final answer a data-backed path.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Move long-running agent calls into an async task queue so the UI can stream intermediate steps instead of waiting for the full result.
- **Safety**: Add a validation layer that checks tool inputs before execution and highlights risky actions in the trace viewer.
- **Performance**: Cache repeated tool results, especially product search and shipping rules, to reduce repeated calls.
- **Observability**: Add a dashboard view with success rate, average latency, average step count, and failure type distribution.
- **UX**: Stream each ReAct step live into the trace panel so users can watch the agent work in real time.

