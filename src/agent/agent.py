import re
import ast
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
        You are an intelligent assistant. You have access to the following tools:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        self.history = [f"User: {user_input}"]
        current_prompt = "\n".join(self.history)
        steps = 0

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result["content"].strip()
            usage = result.get("usage", {})
            latency_ms = result.get("latency_ms", 0)
            tracker.track_request(result.get("provider", "unknown"), self.llm.model_name, usage, latency_ms)
            logger.log_event("AGENT_STEP", {"step": steps + 1, "response": content})

            final_match = re.search(r"Final Answer:\s*(.*)", content, re.IGNORECASE | re.DOTALL)
            if final_match:
                answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps + 1, "success": True})
                return answer

            action = self._parse_action(content)
            if not action:
                self.history.append(content)
                self.history.append(
                    "Observation: No valid Action found. Use exactly: Action: tool_name(arg=value)."
                )
                current_prompt = "\n".join(self.history)
                steps += 1
                continue

            tool_name, args = action
            observation = self._execute_tool(tool_name, args)
            self.history.append(content)
            self.history.append(f"Observation: {observation}")
            current_prompt = "\n".join(self.history)
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "success": False})
        return "I could not produce a final answer within the tool-use step limit."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    kwargs = self._parse_args(tool_name, args)
                    return tool["func"](**kwargs)
                except Exception as exc:
                    return f"Tool execution error for {tool_name}: {exc}"
        return f"Tool {tool_name} not found."

    def _parse_action(self, text: str) -> Optional[tuple[str, str]]:
        match = re.search(r"Action:\s*([a-zA-Z_]\w*)\s*\((.*?)\)", text, re.DOTALL)
        if not match:
            return None
        return match.group(1), match.group(2).strip()

    def _parse_args(self, tool_name: str, args: str) -> Dict[str, Any]:
        if not args:
            return {}

        try:
            parsed = ast.parse(f"f({args})", mode="eval")
            call = parsed.body
            if not isinstance(call, ast.Call):
                return {}

            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
            positional = [ast.literal_eval(arg) for arg in call.args]

            if positional and not kwargs:
                return self._positional_args_to_kwargs(tool_name, positional)
            return kwargs
        except Exception:
            try:
                obj = json.loads(args)
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {"product_name": args.strip("\"'")}

    def _positional_args_to_kwargs(self, tool_name: str, args: List[Any]) -> Dict[str, Any]:
        arg_names = {
            "search_product": ["product_name"],
            "check_stock": ["product_id", "quantity"],
            "get_discount": ["coupon_code"],
            "calc_shipping": ["weight", "destination"],
        }.get(tool_name, [])
        if arg_names:
            return dict(zip(arg_names, args))
        if len(args) == 1:
            return {"product_name": args[0]}
        if len(args) == 2:
            return {"product_id": args[0], "quantity": args[1]}
        return {}
