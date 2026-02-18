"""OpenAI provider using GuardedHttpClient for egress enforcement."""
from __future__ import annotations

import json

from src.core.egress import GuardedHttpClient
from src.plugins.llm_query.providers.base import LLMProvider, LLMResponse

# Rough cost estimates per 1K tokens (input + output averaged)
_COST_PER_1K: dict[str, float] = {
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.0003,
}


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, http_client: GuardedHttpClient) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client

    def provider_name(self) -> str:
        return "openai"

    async def query(self, model: str, prompt: str, max_tokens: int) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="Error: OpenAI API key is not configured. Set OPENAI_API_KEY in environment.",
                model=model,
            )

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        resp = await self._http.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        cost = (total_tokens / 1000) * _COST_PER_1K.get(model, 0.01)

        return LLMResponse(
            text=text,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": total_tokens,
            },
            estimated_cost=cost,
        )

    async def close(self) -> None:
        await self._http.aclose()
