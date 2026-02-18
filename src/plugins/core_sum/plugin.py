"""core.sum — sums two numbers."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.config import AppConfig
from src.core.types import Capability, PluginManifest
from src.plugins._base import ToolContext, ToolPlugin


class SumInput(BaseModel):
    a: float = Field(description="First number")
    b: float = Field(description="Second number")


class SumPlugin(ToolPlugin):
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="core.sum",
            title="Sum",
            description="Returns the sum of two numbers.",
            capabilities=frozenset(),
        )

    def input_model(self) -> type[BaseModel]:
        return SumInput

    async def execute(self, ctx: ToolContext, params: BaseModel) -> str:
        assert isinstance(params, SumInput)
        result = params.a + params.b
        # Return integer if result is whole number
        if result == int(result):
            return str(int(result))
        return str(result)


def create_plugin(**kwargs: Any) -> SumPlugin:
    return SumPlugin()
