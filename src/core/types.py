"""Core domain types shared across the application."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Capability(str, enum.Enum):
    NETWORK_OUTBOUND = "network:outbound"
    LLM_QUERY = "llm:query"
    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    DB_READ = "db:read"
    DB_WRITE = "db:write"


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    tenant_id: str


@dataclass(frozen=True)
class PluginManifest:
    name: str
    title: str
    description: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)

    @staticmethod
    def allow() -> PolicyDecision:
        return PolicyDecision(allowed=True)

    @staticmethod
    def deny(reasons: list[str]) -> PolicyDecision:
        return PolicyDecision(allowed=False, reasons=reasons)

    def merge(self, other: PolicyDecision) -> PolicyDecision:
        """Merge two decisions: denied if either is denied."""
        if self.allowed and other.allowed:
            return PolicyDecision.allow()
        return PolicyDecision(
            allowed=False,
            reasons=self.reasons + other.reasons,
        )
