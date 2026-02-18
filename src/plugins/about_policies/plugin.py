"""about://policies — effective config without secrets, per-agent."""
from __future__ import annotations

import json
from typing import Any

from src.core.config import AppConfig
from src.core.types import AgentIdentity, PluginManifest
from src.plugins._base import ResourcePlugin


class AboutPoliciesPlugin(ResourcePlugin):
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="about.policies",
            title="About Policies",
            description="Effective policy configuration for the requesting agent (secrets redacted).",
        )

    def uri(self) -> str:
        return "about://policies"

    async def read(self, identity: AgentIdentity | None) -> str:
        if identity is None:
            return json.dumps({"error": "Not authenticated"})

        agent_cfg = self._config.agents.get(identity.agent_id)
        if agent_cfg is None:
            return json.dumps({"error": f"Unknown agent: {identity.agent_id}"})

        return json.dumps({
            "agent_id": identity.agent_id,
            "tenant_id": identity.tenant_id,
            "allowed_tools": agent_cfg.allowed_tools,
            "allowed_capabilities": [c.value for c in agent_cfg.allowed_capabilities],
            "egress_allowlist": agent_cfg.egress_allowlist,
            "max_payload_bytes": agent_cfg.max_payload_bytes,
            "max_response_bytes": agent_cfg.max_response_bytes,
            "timeout_seconds": agent_cfg.timeout_seconds,
            "concurrency": agent_cfg.concurrency,
            "rate_limit": agent_cfg.rate_limit,
            "max_tokens_per_request": agent_cfg.max_tokens_per_request,
            "max_cost_per_day": agent_cfg.max_cost_per_day,
            "enabled_plugins": self._config.enabled_plugins,
        }, indent=2)


def create_plugin(config: AppConfig, **kwargs: Any) -> AboutPoliciesPlugin:
    return AboutPoliciesPlugin(config=config)
