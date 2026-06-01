import json
import time
from typing import List, Dict, Any, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.agent.parser import parse_thought, parse_final_answer, parse_action


class ReActAgent:
    """
    ReAct-style Agent following the Thought → Action → Observation loop.
    Supports tool calling, structured logging, and error recovery.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []
        # Quick lookup map: tool_name -> tool dict
        self._tool_map: Dict[str, Dict[str, Any]] = {t["name"]: t for t in tools}

    # ──────────────────────────────────────────────
    # SYSTEM PROMPT
    # ──────────────────────────────────────────────

    def get_system_prompt(self) -> str:
        """
        Build the system prompt that instructs the model to follow ReAct format.
        Lists all available tools and enforces strict output format.
        """
        tool_lines = "\n".join(
            [f'  - {t["name"]}: {t["description"]}' for t in self.tools]
        )

        return f"""You are a smart retail assistant. You must answer by following the ReAct framework strictly.

Available tools:
{tool_lines}

Rules:
1. Always think before acting. Write your reasoning in "Thought:".
2. If you need to call a tool, write exactly:
   Action: tool_name({{"key": "value"}})
3. After seeing the Observation, continue with another Thought/Action or give the Final Answer.
4. When you have enough information, write:
   Final Answer: <your complete answer>
5. NEVER invent data. ALWAYS call tools to get real information.
6. Arguments to tools must be valid JSON inside the parentheses.
7. Do not repeat the same tool call twice with the same arguments.

Format example:
Thought: I need to find the product first.
Action: search_product({{"product_name": "iPhone 15"}})
Observation: {{"id": "p001", "name": "iPhone 15", "price": 25000000, "stock": 10, "weight_kg": 0.2}}
Thought: Now I will check if 2 units are in stock.
Action: check_stock({{"product_id": "p001", "quantity": 2}})
Observation: {{"available": true, "remaining": 8}}
Thought: Now I have all information needed.
Final Answer: iPhone 15 còn hàng. Giá 25,000,000 VNĐ x 2 = 50,000,000 VNĐ.
"""

    # ──────────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────────

    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Execute the ReAct loop.

        Returns a dict with:
            - answer (str)  : Final Answer text
            - trace  (list) : Step-by-step log for the UI (Người 4)
            - steps  (int)  : Number of iterations used
            - error  (str)  : Error message if any, else None
            - latency_s (float): Total wall-clock time
        """
        start_time = time.time()
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        trace: List[Dict[str, Any]] = []
        conversation = user_input  # Grows with each Thought/Action/Observation

        for step in range(1, self.max_steps + 1):
            logger.log_event("AGENT_STEP", {"step": step, "prompt_length": len(conversation)})

            # ── 1. Call LLM ──────────────────────────────────────────────
            try:
                response = self.llm.generate(
                    conversation, system_prompt=self.get_system_prompt()
                )
            except Exception as exc:
                error_msg = f"LLM call failed at step {step}: {exc}"
                logger.log_event("AGENT_ERROR", {"step": step, "error": error_msg})
                return self._build_result(
                    answer="Xin lỗi, có lỗi khi gọi mô hình. Vui lòng thử lại.",
                    trace=trace,
                    steps=step,
                    error=error_msg,
                    latency=time.time() - start_time,
                )

            # ── 2. Parse response (dùng parser.py) ──────────────────────
            thought      = parse_thought(response)
            final_answer = parse_final_answer(response)
            action_name, action_args_str = parse_action(response)

            step_record: Dict[str, Any] = {
                "step": step,
                "thought": thought,
                "action": None,
                "tool_input": None,
                "observation": None,
                "final_answer": final_answer,
            }

            # ── 3. Final Answer → stop loop ──────────────────────────────
            if final_answer:
                trace.append(step_record)
                latency = time.time() - start_time
                logger.log_event("AGENT_END", {
                    "steps": step,
                    "latency_s": round(latency, 2),
                    "answer": final_answer,
                })
                return self._build_result(
                    answer=final_answer, trace=trace, steps=step, latency=latency
                )

            # ── 4. Action → execute tool → append Observation ────────────
            if action_name:
                step_record["action"]     = action_name
                step_record["tool_input"] = action_args_str

                logger.log_event("TOOL_CALL", {
                    "step": step, "tool": action_name, "args": action_args_str
                })

                observation = self._execute_tool(action_name, action_args_str)

                logger.log_event("TOOL_RESULT", {
                    "step": step, "tool": action_name, "result": observation
                })

                step_record["observation"] = observation
                trace.append(step_record)

                # Append full exchange so next iteration has full context
                conversation = (
                    f"{conversation}\n"
                    f"Thought: {thought}\n"
                    f"Action: {action_name}({action_args_str})\n"
                    f"Observation: {observation}\n"
                )
                continue

            # ── 5. Malformed output — nudge the model ───────────────────
            trace.append(step_record)
            conversation = (
                f"{conversation}\n"
                f"{response}\n"
                "Please continue. Either call a tool using Action: or provide Final Answer:\n"
            )

        # ── Max steps exceeded ───────────────────────────────────────────
        latency = time.time() - start_time
        logger.log_event("AGENT_ERROR", {
            "error": "max_steps exceeded", "steps": self.max_steps
        })
        return self._build_result(
            answer="Xin lỗi, không thể trả lời trong số bước cho phép. Hãy thử lại với câu hỏi rõ hơn.",
            trace=trace,
            steps=self.max_steps,
            error="max_steps exceeded",
            latency=latency,
        )

    # ──────────────────────────────────────────────
    # TOOL EXECUTION
    # ──────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Find tool by name, parse JSON args, call the function, return result as string.
        Handles: unknown tool, invalid JSON, missing arguments, runtime errors.
        """
        if tool_name not in self._tool_map:
            available = ", ".join(self._tool_map.keys())
            return json.dumps({
                "error": f"Tool '{tool_name}' not found. Available: {available}"
            })

        tool = self._tool_map[tool_name]
        func = tool.get("function")

        if func is None:
            return json.dumps({"error": f"Tool '{tool_name}' has no callable function."})

        # Parse JSON arguments
        try:
            args: Dict[str, Any] = json.loads(args_str) if args_str.strip() else {}
        except json.JSONDecodeError as exc:
            return json.dumps({
                "error": f"Invalid JSON args for '{tool_name}': {exc}"
            })

        # Call the function
        try:
            result = func(**args)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except TypeError as exc:
            return json.dumps({
                "error": f"Wrong/missing arguments for '{tool_name}': {exc}"
            })
        except Exception as exc:
            return json.dumps({
                "error": f"Tool '{tool_name}' raised an error: {exc}"
            })

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    @staticmethod
    def _build_result(
        answer: str,
        trace: List[Dict[str, Any]],
        steps: int,
        error: Optional[str] = None,
        latency: float = 0.0,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "trace": trace,
            "steps": steps,
            "error": error,
            "latency_s": round(latency, 2),
        }