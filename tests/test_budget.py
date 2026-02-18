"""Tests for LLM budget tracking."""
from __future__ import annotations

from src.core.budget import BudgetTracker
from src.core.config import AppConfig
from src.core.policy import PolicyEngine
from src.core.types import AgentIdentity, Capability, PluginManifest


def test_budget_fresh_agent() -> None:
    tracker = BudgetTracker()
    remaining = tracker.check("agent-x", max_cost_per_day=10.0)
    assert remaining == 10.0


def test_budget_after_spend() -> None:
    tracker = BudgetTracker()
    tracker.record("agent-x", 3.0)
    remaining = tracker.check("agent-x", max_cost_per_day=10.0)
    assert remaining == 7.0


def test_budget_exhausted() -> None:
    tracker = BudgetTracker()
    tracker.record("agent-x", 10.0)
    remaining = tracker.check("agent-x", max_cost_per_day=10.0)
    assert remaining == 0.0


def test_budget_exhausted_denies_tool_call(
    policy_engine: PolicyEngine,
    beta_identity: AgentIdentity,
) -> None:
    """When budget is exhausted, llm.query tool calls should be denied."""
    # Exhaust the budget
    policy_engine.budget_tracker.record(beta_identity.agent_id, 25.0)

    manifest = PluginManifest(
        name="llm.query",
        title="LLM",
        description="llm",
        capabilities=frozenset({Capability.NETWORK_OUTBOUND, Capability.LLM_QUERY}),
    )
    decision = policy_engine.check_tool_call(beta_identity, manifest)
    assert not decision.allowed
    assert any("budget exhausted" in r for r in decision.reasons)
