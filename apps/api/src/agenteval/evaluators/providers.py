"""Real JudgeProvider implementations: an OpenAI-compatible chat completions call (used
for both the real OpenAI API and the mock AI/LLM service, which speaks the same shape at
the real path /v1/chat/completions, see mockllm/app.py), and an Anthropic-compatible
messages call. Settings.judge_base_url picks between a provider's real origin and
MOCK_AI_URL (see core/config.py), so switching from the demo/tests to a real deployment
is a different base URL, never a different code path.
"""

from __future__ import annotations

import httpx

from agenteval.evaluators.schema import ProviderFamily


class OpenAICompatibleJudge:
    """Speaks POST {base_url}/chat/completions, the real OpenAI shape and the shape
    mockllm.app answers at for local development, the demo and tests."""

    def __init__(
        self, http: httpx.AsyncClient, base_url: str, api_key: str, provider: ProviderFamily
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.provider = provider

    async def complete(self, prompt: str, *, model: str) -> tuple[str, str]:
        resp = await self._http.post(
            f"{self._base_url}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            headers={"authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return str(data.get("model", model)), str(content)


class AnthropicCompatibleJudge:
    """Speaks POST {base_url}/messages, the real Anthropic shape; the mock AI/LLM service
    answers at the same path for local development, the demo and tests."""

    def __init__(self, http: httpx.AsyncClient, base_url: str, api_key: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.provider: ProviderFamily = "anthropic"

    async def complete(self, prompt: str, *, model: str) -> tuple[str, str]:
        resp = await self._http.post(
            f"{self._base_url}/messages",
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        return str(data.get("model", model)), str(content)
