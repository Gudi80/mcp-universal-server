"""Local/Ollama-compatible provider using GuardedHttpClient."""
from __future__ import annotations

from src.core.egress import GuardedHttpClient
from src.plugins.llm_query.providers.base import LLMProvider, LLMResponse


class LocalProvider(LLMProvider):
    def __init__(self, base_url: str, http_client: GuardedHttpClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client

    def provider_name(self) -> str:
        return "local"

    async def query(self, model: str, prompt: str, max_tokens: int) -> LLMResponse:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        resp = await self._http.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        return LLMResponse(
            text=data.get("response", ""),
            model=model,
            usage={
                "total_tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            },
            estimated_cost=0.0,
        )

    async def close(self) -> None:
        await self._http.aclose()
