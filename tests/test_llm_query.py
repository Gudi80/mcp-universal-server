"""Tests for llm.query plugin — model allowlist, input guard."""
from __future__ import annotations

import json

import pytest

from src.core.config import AppConfig
from src.core.policy import PolicyEngine
from src.core.types import AgentIdentity
from src.plugins._base import ToolContext
from src.plugins.llm_query.input_guard import check_input
from src.plugins.llm_query.plugin import LLMQueryInput, LLMQueryPlugin


def test_input_guard_accept_normal() -> None:
    reasons = check_input("What is the meaning of life?")
    assert reasons == []


def test_input_guard_reject_oversized() -> None:
    big_input = "x" * 200_000
    reasons = check_input(big_input)
    assert any("exceeds hard limit" in r for r in reasons)


def test_input_guard_reject_repo_paste() -> None:
    # Simulate repo paste with many code fences
    blocks = "\n".join(["```python\ndef foo(): pass\n```"] * 15)
    reasons = check_input(blocks)
    assert any("code fences" in r for r in reasons)


@pytest.mark.anyio
async def test_model_not_in_allowlist(
    sample_config: AppConfig,
    beta_identity: AgentIdentity,
) -> None:
    policy = PolicyEngine(sample_config)
    plugin = LLMQueryPlugin(config=sample_config, policy_engine=policy)

    params = LLMQueryInput(
        provider="openai",
        model="gpt-3.5-turbo",  # Not in allowlist
        prompt="test",
        max_tokens=100,
    )
    ctx = ToolContext(identity=beta_identity, raw_arguments={})
    result = await plugin.execute(ctx, params)
    data = json.loads(result)
    assert "error" in data
    assert "not on the allowlist" in data["error"]


@pytest.mark.anyio
async def test_missing_api_key(
    beta_identity: AgentIdentity,
) -> None:
    """When API key is empty, return user-friendly error, don't crash."""
    from src.core.config import AppConfig, LLMConfig, LLMProviderConfig, AgentConfig, ServerConfig
    from src.core.types import Capability

    config = AppConfig(
        agents={
            "agent-beta": AgentConfig(
                token="t",
                allowed_tools=["llm.query"],
                allowed_capabilities=[Capability.NETWORK_OUTBOUND, Capability.LLM_QUERY],
                egress_allowlist=["api.openai.com"],
            )
        },
        llm=LLMConfig(
            providers={
                "openai": LLMProviderConfig(
                    api_key="",  # Empty key
                    base_url="https://api.openai.com/v1",
                    allowed_models=["gpt-4o"],
                ),
            }
        ),
    )
    policy = PolicyEngine(config)
    plugin = LLMQueryPlugin(config=config, policy_engine=policy)

    params = LLMQueryInput(provider="openai", model="gpt-4o", prompt="test", max_tokens=10)
    ctx = ToolContext(identity=beta_identity, raw_arguments={})
    result = await plugin.execute(ctx, params)
    data = json.loads(result)
    assert "not configured" in data.get("text", data.get("error", ""))
