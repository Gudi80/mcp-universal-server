"""Anthropic provider using GuardedHttpClient for egress enforcement."""
from __future__ import annotations

from src.core.egress import GuardedHttpClient
from src.plugins.llm_query.providers.base import LLMProvider, LLMResponse

_COST_PER_1K: dict[str, float] = {
    "claude-sonnet-4-20250514": 0.006,
    "claude-haiku-4-5-20251001": 0.002,
}


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, http_client: GuardedHttpClient) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client

    def provider_name(self) -> str:
        return "anthropic"

    async def query(self, model: str, prompt: str, max_tokens: int) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                text="Error: Anthropic API key is not configured. Set ANTHROPIC_API_KEY in environment.",
                model=model,
            )

        url = f"{self._base_url}/messages"
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        resp = await self._http.post(
            url,
            json=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        text = "\n".join(text_blocks)
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total = input_tokens + output_tokens
        cost = (total / 1000) * _COST_PER_1K.get(model, 0.005)

        return LLMResponse(
            text=text,
            model=model,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total,
            },
            estimated_cost=cost,
        )

    async def close(self) -> None:
        await self._http.aclose()
