"""Tests for plugin loading and manifest validation."""
from __future__ import annotations

import pytest

from src.core.config import AppConfig
from src.core.policy import PolicyEngine
from src.core.registry import PluginRegistry


def test_load_core_plugins(sample_config: AppConfig) -> None:
    registry = PluginRegistry()
    policy = PolicyEngine(sample_config)
    registry.load(config=sample_config, policy_engine=policy)

    assert "core.echo" in registry.tools
    assert "core.sum" in registry.tools


def test_plugin_manifest_has_name(sample_config: AppConfig) -> None:
    registry = PluginRegistry()
    policy = PolicyEngine(sample_config)
    registry.load(config=sample_config, policy_engine=policy)

    for name, plugin in registry.tools.items():
        manifest = plugin.manifest()
        assert manifest.name == name
        assert manifest.title
        assert manifest.description


def test_echo_plugin_input_model(sample_config: AppConfig) -> None:
    registry = PluginRegistry()
    policy = PolicyEngine(sample_config)
    registry.load(config=sample_config, policy_engine=policy)

    echo = registry.tools["core.echo"]
    model = echo.input_model()
    assert "text" in model.model_fields


def test_sum_plugin_input_model(sample_config: AppConfig) -> None:
    registry = PluginRegistry()
    policy = PolicyEngine(sample_config)
    registry.load(config=sample_config, policy_engine=policy)

    sum_plugin = registry.tools["core.sum"]
    model = sum_plugin.input_model()
    assert "a" in model.model_fields
    assert "b" in model.model_fields


@pytest.mark.anyio
async def test_echo_execute(sample_config: AppConfig) -> None:
    from src.core.types import AgentIdentity
    from src.plugins._base import ToolContext
    from src.plugins.core_echo.plugin import EchoInput, EchoPlugin

    plugin = EchoPlugin()
    ctx = ToolContext(
        identity=AgentIdentity(agent_id="test", tenant_id="test"),
        raw_arguments={"text": "hello"},
    )
    result = await plugin.execute(ctx, EchoInput(text="hello"))
    assert result == "hello"


@pytest.mark.anyio
async def test_sum_execute(sample_config: AppConfig) -> None:
    from src.core.types import AgentIdentity
    from src.plugins._base import ToolContext
    from src.plugins.core_sum.plugin import SumInput, SumPlugin

    plugin = SumPlugin()
    ctx = ToolContext(
        identity=AgentIdentity(agent_id="test", tenant_id="test"),
        raw_arguments={"a": 2, "b": 3},
    )
    result = await plugin.execute(ctx, SumInput(a=2, b=3))
    assert result == "5"


def test_unknown_plugin_skipped(sample_config: AppConfig) -> None:
    """Unknown plugin names should be skipped without error."""
    from src.core.config import AppConfig

    config = AppConfig(enabled_plugins=["nonexistent.plugin"])
    registry = PluginRegistry()
    policy = PolicyEngine(sample_config)
    registry.load(config=config, policy_engine=policy)
    assert len(registry.tools) == 0
