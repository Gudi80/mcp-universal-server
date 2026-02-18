"""Configuration models and YAML loader with ENV expansion."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.core.types import Capability

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    """Recursively expand ${ENV_VAR} references in strings."""
    if isinstance(value, str):
        def _replacer(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")
        return _ENV_PATTERN.sub(_replacer, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


class LLMProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    allowed_models: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    token: str
    tenant_id: str = "default"
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_capabilities: list[Capability] = Field(default_factory=list)
    egress_allowlist: list[str] = Field(default_factory=list)
    max_payload_bytes: int = 1_048_576  # 1 MB
    max_response_bytes: int = 1_048_576
    timeout_seconds: int = 30
    concurrency: int = 5
    rate_limit: int = 60  # requests per minute
    max_tokens_per_request: int = 4096
    max_cost_per_day: float = 10.0  # USD


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    name: str = "mcp-universal-server"
    version: str = "0.1.0"
    description: str = "Remote MCP server for multi-agent Claude Code environments"


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    enabled_plugins: list[str] = Field(default_factory=lambda: ["core.echo", "core.sum"])
    llm: LLMConfig = Field(default_factory=LLMConfig)
    redact_patterns: list[str] = Field(default_factory=lambda: [
        r"(?i)(sk-[a-zA-Z0-9]{20,})",
        r"(?i)(Bearer\s+[a-zA-Z0-9._\-]+)",
        r"(?i)(api[_-]?key\s*[:=]\s*\S+)",
    ])


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """Load configuration from YAML file with ENV variable expansion."""
    path = Path(path)
    if not path.exists():
        return AppConfig()
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        return AppConfig()
    expanded = _expand_env(raw)
    return AppConfig.model_validate(expanded)
