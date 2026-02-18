"""Policy engine: allowlists, capability gating, limits, budget checks.

Every tool call passes through this engine — no bypass path.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.budget import BudgetTracker
from src.core.config import AgentConfig, AppConfig
from src.core.rate_limit import RateLimiter
from src.core.types import AgentIdentity, Capability, PluginManifest, PolicyDecision

if TYPE_CHECKING:
    pass

logger = logging.getLogger("mcp_server")


class PolicyEngine:
    """Central policy enforcement for all tool calls and egress."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._budget = BudgetTracker()
        self._rate_limiter = RateLimiter()

    @property
    def budget_tracker(self) -> BudgetTracker:
        return self._budget

    def _get_agent_config(self, identity: AgentIdentity) -> AgentConfig | None:
        return self._config.agents.get(identity.agent_id)

    def check_tool_call(
        self,
        identity: AgentIdentity,
        manifest: PluginManifest,
        payload_size: int = 0,
    ) -> PolicyDecision:
        """Run all policy checks for a tool call. Returns deny with reasons if any fail."""
        agent_cfg = self._get_agent_config(identity)
        if agent_cfg is None:
            return PolicyDecision.deny([f"Unknown agent: {identity.agent_id}"])

        reasons: list[str] = []

        # 1. Tool allowlist
        if manifest.name not in agent_cfg.allowed_tools:
            reasons.append(
                f"Tool '{manifest.name}' is not in allowed_tools for agent '{identity.agent_id}'"
            )

        # 2. Capability gating
        allowed_caps = frozenset(agent_cfg.allowed_capabilities)
        missing = manifest.capabilities - allowed_caps
        if missing:
            reasons.append(
                f"Missing capabilities: {sorted(c.value for c in missing)}"
            )

        # 3. Payload size
        if payload_size > agent_cfg.max_payload_bytes:
            reasons.append(
                f"Payload size {payload_size} exceeds limit {agent_cfg.max_payload_bytes}"
            )

        # 4. Rate limit
        if not self._rate_limiter.check(identity.agent_id, agent_cfg.rate_limit):
            reasons.append(
                f"Rate limit exceeded: {agent_cfg.rate_limit} requests/minute"
            )

        # 5. LLM budget (only for tools requiring llm:query)
        if Capability.LLM_QUERY in manifest.capabilities:
            remaining = self._budget.check(
                identity.agent_id, agent_cfg.max_cost_per_day
            )
            if remaining <= 0:
                reasons.append(
                    f"Daily LLM budget exhausted (limit: ${agent_cfg.max_cost_per_day:.2f})"
                )

        if reasons:
            logger.warning(
                "Policy deny",
                extra={
                    "agent_id": identity.agent_id,
                    "tool": manifest.name,
                    "reasons": reasons,
                },
            )
            return PolicyDecision.deny(reasons)

        # Record rate limit hit
        self._rate_limiter.record(identity.agent_id)
        return PolicyDecision.allow()

    def check_egress(self, identity: AgentIdentity, host: str) -> PolicyDecision:
        """Check if outbound HTTP to a given host is allowed for this agent."""
        agent_cfg = self._get_agent_config(identity)
        if agent_cfg is None:
            return PolicyDecision.deny([f"Unknown agent: {identity.agent_id}"])

        if Capability.NETWORK_OUTBOUND not in agent_cfg.allowed_capabilities:
            return PolicyDecision.deny(
                [f"Agent '{identity.agent_id}' lacks capability 'network:outbound'"]
            )

        host_lower = host.lower()
        if host_lower not in [h.lower() for h in agent_cfg.egress_allowlist]:
            return PolicyDecision.deny(
                [f"Host '{host}' not in egress allowlist for agent '{identity.agent_id}'"]
            )

        return PolicyDecision.allow()
