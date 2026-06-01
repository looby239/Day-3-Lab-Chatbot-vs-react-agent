import os
import sys
import json
import time
from typing import Dict, Any, List

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.mock_provider import MockProvider
from src.tools.store_tools import TOOLS_METADATA
from tests.test_suite import TEST_CASES
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.agent.agent import ReActAgent

def run_chatbot_baseline(provider: MockProvider, query: str) -> Dict[str, Any]:
    """Runs the baseline chatbot by calling LLM directly."""
    logger.log_event("CHATBOT_START", {"input": query, "model": provider.model_name})
    
    start_time = time.time()
    # In chatbot mode, get system prompt with rules
    system_prompt = (
        "You are a chatbot assistant. You do NOT have access to tools. "
        "You must answer using the operational rules: "
        "only answer topics related to Retail/E-commerce, and do not chat. "
        "If out of topic, refuse using the standard refusal templates."
    )
    
    result = provider.generate(query, system_prompt=system_prompt)
    latency_ms = result["latency_ms"]
    content = result["content"]
    
    # Strip Final Answer if mock provider prepended it
    if content.startswith("Final Answer:"):
        content = content.replace("Final Answer:", "").strip()
        
    usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    tracker.track_request("mock", provider.model_name, usage, latency_ms)
    
    logger.log_event("CHATBOT_END", {"success": True, "output": content})
    
    return {
        "output": content,
        "latency_ms": latency_ms,
        "tokens": usage["total_tokens"],
        "steps": 1
    }

def run_agent(provider: MockProvider, query: str) -> Dict[str, Any]:
    """Runs the ReAct Agent."""
    # Convert tools list format for agent
    tools_list = [{"name": t["name"], "description": t["description"], "func": t["func"]} for t in TOOLS_METADATA]
    
    # We clear tracker session metrics to isolate this task's LLM calls
    tracker.session_metrics = []
    
    agent = ReActAgent(llm=provider, tools=tools_list, max_steps=6)
    
    start_time = time.time()
    output = agent.run(query)
    end_time = time.time()
    
    # Aggregate tracker metrics for this run
    total_latency = sum(m["latency_ms"] for m in tracker.session_metrics)
    total_tokens = sum(m["total_tokens"] for m in tracker.session_metrics)
    steps = len(tracker.session_metrics)
    
    return {
        "output": output,
        "latency_ms": total_latency if total_latency > 0 else int((end_time - start_time) * 1000),
        "tokens": total_tokens,
        "steps": steps
    }

def evaluate_run(output: str, expected_keywords: List[str]) -> bool:
    """Evaluates whether the output contains all expected keywords."""
    output_lower = output.lower()
    for kw in expected_keywords:
        if kw.lower() not in output_lower:
            return False
    return True

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("=" * 60)
    print("RUNNING LAB 3 EVALUATION SUITE")
    print("=" * 60)
    
    modes = ["chatbot", "agent_v1", "agent_v2"]
    results_summary = {}
    
    for mode in modes:
        print(f"\nEvaluating: {mode.upper()}...")
        provider = MockProvider(mode=mode)
        mode_results = []
        
        for case in TEST_CASES:
            query = case["query"]
            expected = case["expected_keywords"]
            
            if mode == "chatbot":
                res = run_chatbot_baseline(provider, query)
            else:
                res = run_agent(provider, query)
                
            success = evaluate_run(res["output"], expected)
            
            mode_results.append({
                "id": case["id"],
                "name": case["name"],
                "category": case["category"],
                "success": success,
                "latency_ms": res["latency_ms"],
                "tokens": res["tokens"],
                "steps": res["steps"],
                "output": res["output"]
            })
            
            status = "PASS" if success else "FAIL"
            print(f"  - Case {case['id']}: {case['name']} -> {status} (Steps: {res['steps']}, Latency: {res['latency_ms']}ms, Tokens: {res['tokens']})")
            
        results_summary[mode] = mode_results

    # Print Aggregate Metrics
    print("\n" + "=" * 60)
    print("EVALUATION METRICS SUMMARY")
    print("=" * 60)
    
    for mode, results in results_summary.items():
        total_cases = len(results)
        passed = sum(1 for r in results if r["success"])
        success_rate = (passed / total_cases) * 100
        avg_latency = sum(r["latency_ms"] for r in results) / total_cases
        avg_tokens = sum(r["tokens"] for r in results) / total_cases
        avg_loops = sum(r["steps"] for r in results) / total_cases
        
        print(f"\nConfiguration: {mode.upper()}")
        print(f"  - Success Rate: {success_rate:.1f}% ({passed}/{total_cases} passed)")
        print(f"  - Average Latency: {avg_latency:.1f} ms")
        print(f"  - Average Tokens/Task: {avg_tokens:.1f} tokens")
        print(f"  - Average Loop Count: {avg_loops:.2f} steps")

    # Save summary report to JSON
    summary_path = "logs/evaluation_summary.json"
    if not os.path.exists("logs"):
        os.makedirs("logs")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed evaluation results saved to {summary_path}")

if __name__ == "__main__":
    main()
