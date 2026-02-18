"""llm.query plugin — LLM router with model allowlist and budget tracking."""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from src.core.config import AppConfig
from src.core.egress import GuardedHttpClient
from src.core.policy import PolicyEngine
from src.core.types import Capability, PluginManifest
from src.plugins._base import ToolContext, ToolPlugin
from src.plugins.llm_query.input_guard import check_input
from src.plugins.llm_query.providers.anthropic import AnthropicProvider
from src.plugins.llm_query.providers.base import LLMProvider
from src.plugins.llm_query.providers.local import LocalProvider
from src.plugins.llm_query.providers.openai import OpenAIProvider

logger = logging.getLogger("mcp_server")


class LLMQueryInput(BaseModel):
    provider: str = Field(description="LLM provider: 'openai', 'anthropic', or 'local'")
    model: str = Field(description="Model name (must be on allowlist)")
    prompt: str = Field(description="The prompt to send to the LLM")
    max_tokens: int = Field(default=1024, description="Maximum tokens in response")


class LLMQueryPlugin(ToolPlugin):
    def __init__(self, config: AppConfig, policy_engine: PolicyEngine) -> None:
        self._config = config
        self._policy = policy_engine
        self._providers: dict[str, LLMProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        for name, pcfg in self._config.llm.providers.items():
            # Each provider gets its own GuardedHttpClient with egress enforced
            # via the global allowlist (providers must be on agent's egress allowlist)
            if name == "openai":
                http_client = GuardedHttpClient(
                    allowlist=["api.openai.com"],
                    timeout=60.0,
                )
                self._providers["openai"] = OpenAIProvider(
                    api_key=pcfg.api_key,
                    base_url=pcfg.base_url or "https://api.openai.com/v1",
                    http_client=http_client,
                )
            elif name == "anthropic":
                http_client = GuardedHttpClient(
                    allowlist=["api.anthropic.com"],
                    timeout=60.0,
                )
                self._providers["anthropic"] = AnthropicProvider(
                    api_key=pcfg.api_key,
                    base_url=pcfg.base_url or "https://api.anthropic.com/v1",
                    http_client=http_client,
                )
            elif name == "local":
                from urllib.parse import urlparse
                host = urlparse(pcfg.base_url or "http://localhost:11434").hostname or "localhost"
                http_client = GuardedHttpClient(
                    allowlist=[host],
                    timeout=120.0,
                )
                self._providers["local"] = LocalProvider(
                    base_url=pcfg.base_url or "http://localhost:11434",
                    http_client=http_client,
                )

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="llm.query",
            title="LLM Query",
            description="Route queries to LLM providers (OpenAI, Anthropic, local). "
            "Requires network:outbound and llm:query capabilities.",
            capabilities=frozenset({Capability.NETWORK_OUTBOUND, Capability.LLM_QUERY}),
        )

    def input_model(self) -> type[BaseModel]:
        return LLMQueryInput

    async def execute(self, ctx: ToolContext, params: BaseModel) -> str:
        assert isinstance(params, LLMQueryInput)
        identity = ctx.identity
        agent_cfg = self._config.agents.get(identity.agent_id)
        if agent_cfg is None:
            return json.dumps({"error": f"Unknown agent: {identity.agent_id}"})

        # Check egress allowlist for the provider
        egress_decision = self._policy.check_egress(identity, self._get_provider_host(params.provider))
        if not egress_decision.allowed:
            return json.dumps({"error": "Egress denied", "reasons": egress_decision.reasons})

        # Check provider exists
        provider = self._providers.get(params.provider)
        if provider is None:
            return json.dumps({"error": f"Unknown provider: {params.provider}"})

        # Check model allowlist
        pcfg = self._config.llm.providers.get(params.provider)
        if pcfg is None or params.model not in pcfg.allowed_models:
            return json.dumps({
                "error": f"Model '{params.model}' is not on the allowlist for provider '{params.provider}'"
            })

        # Input guard
        guard_reasons = check_input(params.prompt)
        if guard_reasons:
            return json.dumps({"error": "Input rejected", "reasons": guard_reasons})

        # Cap max_tokens to agent limit
        max_tokens = min(params.max_tokens, agent_cfg.max_tokens_per_request)

        # Execute query
        try:
            response = await provider.query(params.model, params.prompt, max_tokens)
        except Exception as exc:
            logger.exception("LLM query failed", extra={"provider": params.provider, "model": params.model})
            return json.dumps({"error": f"LLM query failed: {exc}"})

        # Record cost in budget tracker
        if response.estimated_cost > 0:
            self._policy.budget_tracker.record(identity.agent_id, response.estimated_cost)

        return json.dumps({
            "text": response.text,
            "model": response.model,
            "usage": response.usage,
            "estimated_cost": response.estimated_cost,
        })

    def _get_provider_host(self, provider_name: str) -> str:
        hosts = {
            "openai": "api.openai.com",
            "anthropic": "api.anthropic.com",
            "local": "localhost",
        }
        return hosts.get(provider_name, "unknown")


def create_plugin(config: AppConfig, policy_engine: PolicyEngine, **kwargs: Any) -> LLMQueryPlugin:
    return LLMQueryPlugin(config=config, policy_engine=policy_engine)
