"""about://server — server name, version, description."""
from __future__ import annotations

import json
from typing import Any

from src.core.config import AppConfig
from src.core.types import AgentIdentity, PluginManifest
from src.plugins._base import ResourcePlugin


class AboutServerPlugin(ResourcePlugin):
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="about.server",
            title="About Server",
            description="Server name, version, and description.",
        )

    def uri(self) -> str:
        return "about://server"

    async def read(self, identity: AgentIdentity | None) -> str:
        return json.dumps({
            "name": self._config.server.name,
            "version": self._config.server.version,
            "description": self._config.server.description,
        }, indent=2)


def create_plugin(config: AppConfig, **kwargs: Any) -> AboutServerPlugin:
    return AboutServerPlugin(config=config)
