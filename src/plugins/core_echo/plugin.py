"""core.echo — returns the input text unchanged."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.config import AppConfig
from src.core.types import Capability, PluginManifest
from src.plugins._base import ToolContext, ToolPlugin


class EchoInput(BaseModel):
    text: str = Field(description="Text to echo back")


class EchoPlugin(ToolPlugin):
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="core.echo",
            title="Echo",
            description="Returns the input text unchanged.",
            capabilities=frozenset(),
        )

    def input_model(self) -> type[BaseModel]:
        return EchoInput

    async def execute(self, ctx: ToolContext, params: BaseModel) -> str:
        assert isinstance(params, EchoInput)
        return params.text


def create_plugin(**kwargs: Any) -> EchoPlugin:
    return EchoPlugin()
