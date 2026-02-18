"""Tests for policy engine."""
from __future__ import annotations

from src.core.policy import PolicyEngine
from src.core.types import AgentIdentity, Capability, PluginManifest


def test_allow_tool_on_allowlist(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    manifest = PluginManifest(name="core.echo", title="Echo", description="echo")
    decision = policy_engine.check_tool_call(alpha_identity, manifest)
    assert decision.allowed


def test_deny_tool_not_on_allowlist(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    manifest = PluginManifest(name="llm.query", title="LLM", description="llm")
    decision = policy_engine.check_tool_call(alpha_identity, manifest)
    assert not decision.allowed
    assert any("not in allowed_tools" in r for r in decision.reasons)


def test_capability_gating_deny(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    """Agent alpha lacks network:outbound capability."""
    manifest = PluginManifest(
        name="core.echo",  # on allowlist but requires missing capability
        title="Echo",
        description="echo",
        capabilities=frozenset({Capability.NETWORK_OUTBOUND}),
    )
    decision = policy_engine.check_tool_call(alpha_identity, manifest)
    assert not decision.allowed
    assert any("Missing capabilities" in r for r in decision.reasons)


def test_capability_gating_allow(
    policy_engine: PolicyEngine,
    beta_identity: AgentIdentity,
) -> None:
    """Agent beta has network:outbound and llm:query."""
    manifest = PluginManifest(
        name="llm.query",
        title="LLM",
        description="llm",
        capabilities=frozenset({Capability.NETWORK_OUTBOUND, Capability.LLM_QUERY}),
    )
    decision = policy_engine.check_tool_call(beta_identity, manifest)
    assert decision.allowed


def test_payload_size_deny(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    manifest = PluginManifest(name="core.echo", title="Echo", description="echo")
    decision = policy_engine.check_tool_call(
        alpha_identity, manifest, payload_size=2_000_000
    )
    assert not decision.allowed
    assert any("Payload size" in r for r in decision.reasons)


def test_unknown_agent(policy_engine: PolicyEngine) -> None:
    unknown = AgentIdentity(agent_id="unknown-agent", tenant_id="x")
    manifest = PluginManifest(name="core.echo", title="Echo", description="echo")
    decision = policy_engine.check_tool_call(unknown, manifest)
    assert not decision.allowed
    assert any("Unknown agent" in r for r in decision.reasons)


def test_multiple_deny_reasons(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    """Tool not on allowlist AND requires missing capability."""
    manifest = PluginManifest(
        name="llm.query",
        title="LLM",
        description="llm",
        capabilities=frozenset({Capability.NETWORK_OUTBOUND}),
    )
    decision = policy_engine.check_tool_call(alpha_identity, manifest)
    assert not decision.allowed
    assert len(decision.reasons) >= 2
