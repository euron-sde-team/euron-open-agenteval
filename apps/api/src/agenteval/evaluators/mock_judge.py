"""A deterministic, in-process JudgeProvider for unit tests: no HTTP, no event loop
dependency on a running mock service, just the same scoring convention the real mockllm
service uses (see mockllm/app.py's module docstring), so a unit test can assert on an
exact score without any network at all. Call count is tracked on the instance, the exact
mechanism AC3's "zero judge calls" test needs.
"""

from __future__ import annotations

import json

from agenteval.evaluators.schema import ProviderFamily

_SCORE_RULES: list[tuple[str, float]] = [
    ("flawless", 1.0),
    ("perfect", 1.0),
    ("good enough", 0.8),
    ("partially", 0.5),
    ("wrong", 0.0),
    ("fails", 0.0),
]


def score_for_text(text: str) -> float:
    """The same convention mockllm.app uses: a keyword anywhere in the prompt (which
    always embeds the agent's own response text) picks a fixed score, so a test can
    control exactly what the mock judge returns by writing a fake agent output that
    contains one of these words. The default (no keyword present) is 0.9, a clear pass
    without being a suspicious round number."""
    lowered = text.lower()
    for keyword, score in _SCORE_RULES:
        if keyword in lowered:
            return score
    return 0.9


class MockJudgeProvider:
    provider: ProviderFamily = "mock"

    def __init__(self) -> None:
        self.call_count = 0

    async def complete(self, prompt: str, *, model: str) -> tuple[str, str]:
        self.call_count += 1
        score = score_for_text(prompt)
        raw = json.dumps({"score": score, "reasoning": f"mock judge scored {score}"})
        return model, raw
