"""Abstract base classes for plugins."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from src.core.types import AgentIdentity, PluginManifest


@dataclass
class ToolContext:
    """Context passed to tool plugin execute method."""
    identity: AgentIdentity
    raw_arguments: dict[str, Any]


class ToolPlugin(abc.ABC):
    @abc.abstractmethod
    def manifest(self) -> PluginManifest:
        ...

    @abc.abstractmethod
    def input_model(self) -> type[BaseModel]:
        """Return the Pydantic model describing the tool's input schema."""
        ...

    @abc.abstractmethod
    async def execute(self, ctx: ToolContext, params: BaseModel) -> str:
        """Execute the tool and return a string result."""
        ...


class ResourcePlugin(abc.ABC):
    @abc.abstractmethod
    def manifest(self) -> PluginManifest:
        ...

    @abc.abstractmethod
    def uri(self) -> str:
        """Return the resource URI, e.g. 'about://server'."""
        ...

    @abc.abstractmethod
    async def read(self, identity: AgentIdentity | None) -> str:
        """Read the resource content."""
        ...


class PromptPlugin(abc.ABC):
    @abc.abstractmethod
    def manifest(self) -> PluginManifest:
        ...

    @abc.abstractmethod
    def prompt_name(self) -> str:
        """Return the prompt name, e.g. 'review_pr'."""
        ...

    @abc.abstractmethod
    def arguments(self) -> list[dict[str, Any]]:
        """Return list of prompt argument descriptors."""
        ...

    @abc.abstractmethod
    async def render(self, args: dict[str, str]) -> str:
        """Render the prompt template with the given arguments."""
        ...
