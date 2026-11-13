"""Deterministic stand-in for a real LLM provider's chat/completion endpoints, used by
judge-based evaluation metrics, the demo and the integration test suite so none of them
need a real provider API key or network access.

Routes answer at the same real paths the OpenAI and Anthropic APIs expose
(``/chat/completions``, ``/messages``), so pointing AgentEval's judge base URL at a real
provider's origin instead of this mock needs no code change (see core/config.py's
Settings.judge_base_url and MOCK_AI_URL).

Scoring convention, shared with evaluators/mock_judge.py's in-process equivalent used by
unit tests: a keyword anywhere in the prompt (which always embeds the agent's own
response text) picks a fixed score, so a test can control exactly what the mock judge
returns by writing a fake agent output that contains one of these words. No keyword
present scores 0.9, a clear pass without being a suspicious round number.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request

app = FastAPI(title="agenteval mock AI/LLM service")

_CALL_COUNTS: dict[str, int] = {"chat-completions": 0, "messages": 0}

_SCORE_RULES: list[tuple[str, float]] = [
    ("flawless", 1.0),
    ("perfect", 1.0),
    ("good enough", 0.8),
    ("partially", 0.5),
    ("wrong", 0.0),
    ("fails", 0.0),
]


def _score_for_text(text: str) -> float:
    lowered = text.lower()
    for keyword, score in _SCORE_RULES:
        if keyword in lowered:
            return score
    return 0.9


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
async def stats() -> dict[str, int]:
    return dict(_CALL_COUNTS)


@app.post("/reset", summary="Test helper: zero every call counter")
async def reset() -> dict[str, int]:
    for key in _CALL_COUNTS:
        _CALL_COUNTS[key] = 0
    return dict(_CALL_COUNTS)


@app.post("/chat/completions", summary="Stand-in for the real OpenAI chat completions endpoint")
async def chat_completions(request: Request) -> dict[str, object]:
    _CALL_COUNTS["chat-completions"] += 1
    body = await request.json()
    model = body.get("model", "mock-model")
    prompt = " ".join(m.get("content", "") for m in body.get("messages", []))
    score = _score_for_text(prompt)
    content = json.dumps({"score": score, "reasoning": f"mock judge scored {score}"})
    return {
        "id": "mock-completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
    }


@app.post("/messages", summary="Stand-in for the real Anthropic messages endpoint")
async def messages(request: Request) -> dict[str, object]:
    _CALL_COUNTS["messages"] += 1
    body = await request.json()
    model = body.get("model", "mock-model")
    prompt = " ".join(m.get("content", "") for m in body.get("messages", []))
    score = _score_for_text(prompt)
    content = json.dumps({"score": score, "reasoning": f"mock judge scored {score}"})
    return {
        "id": "mock-message",
        "model": model,
        "content": [{"type": "text", "text": content}],
    }
