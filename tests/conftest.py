"""Shared test fixtures."""
from __future__ import annotations

import pytest

from src.core.config import AgentConfig, AppConfig, LLMConfig, LLMProviderConfig, ServerConfig
from src.core.policy import PolicyEngine
from src.core.types import AgentIdentity, Capability


@pytest.fixture
def sample_config() -> AppConfig:
    return AppConfig(
        server=ServerConfig(name="test-server", version="0.0.1"),
        agents={
            "agent-alpha": AgentConfig(
                token="token-alpha-secret",
                tenant_id="team-a",
                allowed_tools=["core.echo", "core.sum"],
                allowed_capabilities=[],
                egress_allowlist=[],
                rate_limit=60,
                max_payload_bytes=1_048_576,
                max_cost_per_day=10.0,
            ),
            "agent-beta": AgentConfig(
                token="token-beta-secret",
                tenant_id="team-b",
                allowed_tools=["core.echo", "core.sum", "llm.query"],
                allowed_capabilities=[
                    Capability.NETWORK_OUTBOUND,
                    Capability.LLM_QUERY,
                ],
                egress_allowlist=["api.openai.com", "api.anthropic.com"],
                rate_limit=30,
                max_payload_bytes=1_048_576,
                max_cost_per_day=25.0,
                max_tokens_per_request=8192,
            ),
        },
        enabled_plugins=["core.echo", "core.sum"],
        llm=LLMConfig(
            providers={
                "openai": LLMProviderConfig(
                    api_key="sk-test-key",
                    base_url="https://api.openai.com/v1",
                    allowed_models=["gpt-4o", "gpt-4o-mini"],
                ),
                "anthropic": LLMProviderConfig(
                    api_key="sk-ant-test-key",
                    base_url="https://api.anthropic.com/v1",
                    allowed_models=["claude-sonnet-4-20250514"],
                ),
            }
        ),
    )


@pytest.fixture
def alpha_identity() -> AgentIdentity:
    return AgentIdentity(agent_id="agent-alpha", tenant_id="team-a")


@pytest.fixture
def beta_identity() -> AgentIdentity:
    return AgentIdentity(agent_id="agent-beta", tenant_id="team-b")


@pytest.fixture
def policy_engine(sample_config: AppConfig) -> PolicyEngine:
    return PolicyEngine(sample_config)
