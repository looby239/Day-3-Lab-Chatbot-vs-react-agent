import re
from typing import Optional, Tuple


def parse_thought(text: str) -> Optional[str]:
    """
    Extract 'Thought: ...' from LLM response.
    Stops before Action: or Final Answer:
    """
    match = re.search(
        r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|\Z)",
        text,
        re.DOTALL,
    )
    return match.group(1).strip() if match else None


def parse_final_answer(text: str) -> Optional[str]:
    """
    Extract 'Final Answer: ...' from LLM response.
    Captures everything after the marker.
    """
    match = re.search(r"Final Answer:\s*(.+)", text, re.DOTALL)
    return match.group(1).strip() if match else None


def parse_action(text: str) -> Tuple[Optional[str], str]:
    """
    Extract tool name and JSON args from 'Action: tool_name({...})'.

    Returns:
        (tool_name, args_json_str)  if found
        (None, "")                  if not found

    Handles two patterns:
        Action: search_product({"product_name": "iPhone 15"})   <- strict
        Action: search_product({"product_name": "iPhone 15"})   <- multiline args
    """
    # Pattern 1: strict — args is a JSON object {...}
    match = re.search(
        r"Action:\s*(\w+)\s*\(\s*(\{.*?\})\s*\)",
        text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Pattern 2: fallback — grab everything inside the parentheses
    match = re.search(
        r"Action:\s*(\w+)\s*\((.+?)\)\s*(?:\n|$)",
        text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return None, ""