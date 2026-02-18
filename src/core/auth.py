"""Bearer token authentication: token → AgentIdentity."""
from __future__ import annotations

import hmac

from src.core.config import AppConfig
from src.core.types import AgentIdentity


class AuthService:
    """Resolves bearer tokens to agent identities using constant-time comparison."""

    def __init__(self, config: AppConfig) -> None:
        self._token_map: dict[str, AgentIdentity] = {}
        for agent_id, agent_cfg in config.agents.items():
            if agent_cfg.token:
                self._token_map[agent_cfg.token] = AgentIdentity(
                    agent_id=agent_id,
                    tenant_id=agent_cfg.tenant_id,
                )

    def resolve(self, token: str) -> AgentIdentity | None:
        """Resolve a bearer token to an AgentIdentity, or None if invalid.

        Uses constant-time comparison to prevent timing attacks.
        """
        for stored_token, identity in self._token_map.items():
            if hmac.compare_digest(stored_token, token):
                return identity
        return None
