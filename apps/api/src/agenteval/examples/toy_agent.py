"""A toy agent for the quickstart, the demo seed, and this smoke test's python adapter:
not a real agent, just a deterministic stand-in with a predictable output shape, so
`agenteval seed-demo` and a fresh `make up` need no real agent framework or API key to
exercise an evaluation end to end (docs/PLAN.md's scope section)."""

from __future__ import annotations

from typing import Any


def answer(test_input: dict[str, Any]) -> dict[str, Any]:
    """Echoes back a canned answer for a known question, and calls a 'calculator' tool
    for anything that looks like arithmetic, so both deterministic and tool-calling test
    cases have something real to score against."""
    question = str(test_input.get("question", ""))
    if "capital of france" in question.lower():
        return {"text": "The capital of France is Paris."}
    if "2 + 2" in question or "2+2" in question:
        return {
            "text": "2 + 2 is 4.",
            "tool_calls": [{"name": "calculator", "arguments": {"expression": "2 + 2"}}],
        }
    return {"text": f"I'm not sure how to answer: {question}"}
