"""Abstract base for LLM providers."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    estimated_cost: float = 0.0


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def provider_name(self) -> str:
        ...

    @abc.abstractmethod
    async def query(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        ...
