"""The demo seed's own two agent versions: a baseline and a candidate with a realistic
trade-off (a prompt change that regresses one metric while improving another), so
`make demo`'s benchmark comparison shows a genuine mix, not a staged, one-sided result."""

from __future__ import annotations

from typing import Any


def answer_v1(test_input: dict[str, Any]) -> dict[str, Any]:
    question = str(test_input.get("question", ""))
    if "capital of france" in question.lower():
        return {"text": "The capital of France is Paris."}
    if "2 + 2" in question:
        return {
            "text": "2 + 2 is 4.",
            "tool_calls": [{"name": "calculator", "arguments": {"expression": "2 + 2"}}],
        }
    if "sky is blue" in question.lower():
        return {
            "text": (
                "Molecules in the atmosphere scatter shorter blue wavelengths of "
                "sunlight more than longer wavelengths, an effect called Rayleigh "
                "scattering, which is why we see a blue sky."
            )
        }
    if "account balance" in question.lower():
        # A real bug v1 has: it calls account_lookup with no account identifier at all,
        # since the question alone never names an account, exactly the forbidden_tool_calls
        # case docs/PLAN.md's deterministic checks are meant to catch.
        return {
            "text": "Here's your balance.",
            "tool_calls": [{"name": "account_lookup", "arguments": {}}],
        }
    return {"text": f"I'm not sure how to answer: {question}"}


def answer_v2(test_input: dict[str, Any]) -> dict[str, Any]:
    """A prompt change that made the agent hedge on a previously exact factual answer
    (regressing exact_match) while writing a noticeably better, more concise answer to
    the open-ended science question (improving the judge-scored instruction_adherence
    metric, which rewards following the "one sentence" instruction precisely)."""
    question = str(test_input.get("question", ""))
    if "capital of france" in question.lower():
        return {"text": "I believe the capital of France is Paris, though I'd double check."}
    if "2 + 2" in question:
        return {
            "text": "2 + 2 is 4.",
            "tool_calls": [{"name": "calculator", "arguments": {"expression": "2 + 2"}}],
        }
    if "sky is blue" in question.lower():
        return {
            "text": "The sky looks blue because air molecules scatter blue light more than other colors."
        }
    if "account balance" in question.lower():
        # The fix: no account was named, so v2 correctly asks the user to sign in
        # instead of calling account_lookup with nothing to look up.
        return {"text": "I'd need you to sign in first before I can check an account balance."}
    return {"text": f"I'm not sure how to answer: {question}"}
