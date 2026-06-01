# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Retail ReAct Agent Team
- **Team Members**: La_Duy_Anh (UX + Log Viewer), [Update member names]
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

Our project implements a retail/e-commerce assistant for an electronics store. The lab compares a normal chatbot baseline against a ReAct agent that can call tools for product search, stock checking, coupon lookup, and shipping calculation.

- **Scenario**: "I want to buy 2 iPhone 15, use coupon WINNER, and ship to Hanoi. What is the total cost and is it in stock?"
- **Evaluation Run**: `python compare_chatbot_agent.py mock`
- **Chatbot Baseline Success Rate**: 2/10 test cases
- **ReAct Agent Success Rate**: 10/10 test cases
- **Key Outcome**: The agent solved multi-step retail queries more reliably because it used tool observations instead of guessing product, stock, coupon, and shipping information.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

The agent follows this flow:

```text
User query
   -> Phi-3 / Mock provider generates Thought + Action
   -> Agent parses Action
   -> Agent executes retail tool
   -> Tool returns Observation
   -> Observation is appended to the next prompt
   -> Loop repeats until Final Answer or max_steps
```

The UX exposes the same flow:

```text
Streamlit UI
   -> Chatbot Baseline or ReAct Agent
   -> Trace panel
   -> JSON log viewer
```

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `search_product` | `product_name: str` | Find product details such as id, price, stock, and weight. |
| `check_stock` | `product_id: str, quantity: int` | Verify whether the requested quantity is available. |
| `get_discount` | `coupon_code: str` | Retrieve coupon information and discount percentage. |
| `calc_shipping` | `weight: float, destination: str` | Calculate shipping fee by weight and destination city. |

### 2.3 LLM Providers Used

- **Primary Target**: Phi-3 local model through `LocalProvider`.
- **Demo/Evaluation Fallback**: `MockProvider`, used when the Phi-3 GGUF model is not available locally.
- **Optional Providers**: OpenAI and Gemini providers remain available through the provider interface.

---

## 3. Telemetry & Performance Dashboard

Telemetry is logged as JSON through `src/telemetry/logger.py` and metrics are tracked through `src/telemetry/metrics.py`.

Important event types:

- `CHATBOT_BASELINE_START`
- `CHATBOT_BASELINE_END`
- `AGENT_START`
- `AGENT_STEP`
- `TOOL_CALL`
- `AGENT_END`
- `AGENT_ERROR`
- `LLM_METRIC`
- `UX_PROVIDER_FALLBACK`

From the mock evaluation run:

- **Chatbot Baseline**: 2/10 passed
- **ReAct Agent**: 10/10 passed
- **Main multi-step agent query**:
  - Steps: 5
  - Total LLM latency from metrics: about 900 ms
  - Total tokens from metrics: about 952
  - Tool calls: `search_product`, `check_stock`, `calc_shipping`, `get_discount`
- **Main multi-step chatbot query**:
  - Steps: 1
  - Latency: about 220 ms
  - Tokens: about 64

Interpretation: the chatbot is faster and cheaper for simple responses, but the ReAct agent is more reliable for multi-step tasks requiring store data.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Chatbot Hallucinated Shipping

- **Input**: "I want to buy 2 iPhone 15, use coupon WINNER, ship to Hanoi. What is the total cost and is it in stock?"
- **Observation**: The baseline chatbot answered directly and claimed shipping to Hanoi was free.
- **Root Cause**: The chatbot baseline had no access to stock, coupon, or shipping tools. It generated a plausible answer without checking store data.
- **Fix**: Use the ReAct agent so the system calls:
  - `search_product(product_name="iPhone 15")`
  - `check_stock(product_id="prod_iphone15", quantity=2)`
  - `calc_shipping(weight=0.4, destination="Ha Noi")`
  - `get_discount(coupon_code="WINNER")`

### Case Study 2: Local Phi-3 Model Missing

- **Input**: Any query in the web UI when Phi-3 model file is missing.
- **Observation**: The provider could not load `./models/Phi-3-mini-4k-instruct-q4.gguf`.
- **Root Cause**: The local GGUF model was not downloaded in the current environment.
- **Fix**: Add fallback behavior in the UX adapters. The system logs `UX_PROVIDER_FALLBACK` and uses `MockProvider` so the demo remains available.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Chatbot Baseline vs ReAct Agent

| Case Type | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple product search | Failed expected keywords | Passed | Agent |
| Multi-step purchase | Hallucinated/missed details | Passed with tool calls | Agent |
| Out of stock | Hallucinated stock | Passed | Agent |
| Invalid coupon | Unverified answer | Passed | Agent |
| Out-of-bounds topic | Passed refusal | Passed refusal | Draw |
| Prompt injection | Passed refusal | Passed refusal | Draw |

Summary from `logs/baseline_vs_agent.json`:

```text
Chatbot baseline: 2/10 passed
ReAct agent: 10/10 passed
```

### Experiment 2: Agent v1 vs Agent v2

Agent v1 intentionally demonstrates common failures such as wrong tool names or action format issues. Agent v2 improves the tool-use sequence and produces more stable traces for the main retail scenarios.

- **v1 failure example**: calling an incorrect tool name like `calc_ship`.
- **v2 improvement**: calls the available tool `calc_shipping`.
- **Result**: v2 is easier to debug and produces cleaner traces for the UX log viewer.

---

## 6. Production Readiness Review

- **Security**: Validate all tool arguments before execution. Reject prompt injection and out-of-domain requests.
- **Guardrails**: Keep `max_steps` to prevent infinite loops and unexpected cost.
- **Fallback**: Keep provider fallback for demo reliability, but clearly mark when mock mode is used.
- **Observability**: Continue logging `LLM_METRIC`, `TOOL_CALL`, and `AGENT_END` for every run.
- **Scaling**: For a production system, move from a simple loop to a graph-based agent runtime such as LangGraph.
- **UX**: Stream ReAct steps live instead of waiting until the final answer.

---

## 7. Run Instructions

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the web demo:

```powershell
python -m streamlit run src/app.py
```

Open:

```text
http://localhost:8501
```

Run evaluation:

```powershell
python compare_chatbot_agent.py mock
```

