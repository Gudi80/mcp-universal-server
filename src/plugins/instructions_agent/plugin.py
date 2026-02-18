"""instructions://agent — per-agent instructions loaded at session start."""
from __future__ import annotations

import json
from typing import Any

from src.core.config import AppConfig
from src.core.types import AgentIdentity, PluginManifest
from src.plugins._base import ResourcePlugin


class InstructionsAgentPlugin(ResourcePlugin):
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="instructions.agent",
            title="Agent Instructions",
            description="Per-agent instructions loaded at session start and after context clearing.",
        )

    def uri(self) -> str:
        return "instructions://agent"

    async def read(self, identity: AgentIdentity | None) -> str:
        if identity is None:
            return json.dumps({"error": "Not authenticated"})

        agent_cfg = self._config.agents.get(identity.agent_id)
        if agent_cfg is None:
            return json.dumps({"error": f"Unknown agent: {identity.agent_id}"})

        if not agent_cfg.instructions:
            return json.dumps({
                "agent_id": identity.agent_id,
                "instructions": "(no per-agent instructions configured)",
            })

        return agent_cfg.instructions


def create_plugin(config: AppConfig, **kwargs: Any) -> InstructionsAgentPlugin:
    return InstructionsAgentPlugin(config=config)
