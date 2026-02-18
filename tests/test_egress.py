"""Tests for egress enforcement."""
from __future__ import annotations

import pytest

from src.core.egress import EgressDeniedError, GuardedHttpClient
from src.core.policy import PolicyEngine
from src.core.types import AgentIdentity


def test_egress_allow(
    policy_engine: PolicyEngine,
    beta_identity: AgentIdentity,
) -> None:
    decision = policy_engine.check_egress(beta_identity, "api.openai.com")
    assert decision.allowed


def test_egress_deny_host_not_on_allowlist(
    policy_engine: PolicyEngine,
    beta_identity: AgentIdentity,
) -> None:
    decision = policy_engine.check_egress(beta_identity, "evil.example.com")
    assert not decision.allowed
    assert any("not in egress allowlist" in r for r in decision.reasons)


def test_egress_deny_no_capability(
    policy_engine: PolicyEngine,
    alpha_identity: AgentIdentity,
) -> None:
    """Agent alpha lacks network:outbound capability."""
    decision = policy_engine.check_egress(alpha_identity, "api.openai.com")
    assert not decision.allowed
    assert any("network:outbound" in r for r in decision.reasons)


def test_guarded_client_blocks_unlisted_host() -> None:
    client = GuardedHttpClient(allowlist=["api.openai.com"])
    with pytest.raises(EgressDeniedError):
        client._check("https://evil.example.com/path")


def test_guarded_client_allows_listed_host() -> None:
    client = GuardedHttpClient(allowlist=["api.openai.com"])
    # Should not raise
    client._check("https://api.openai.com/v1/chat/completions")
