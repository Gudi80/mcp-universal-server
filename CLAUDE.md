# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mcp-universal-server** — a remote MCP (Model Context Protocol) server using Streamable HTTP transport, designed for multiple Claude Code agents on a LAN/VPN. Priority: security (hard guardrails), multi-tenancy, audit. Full requirements spec (in Polish): `req/mcp.md`.

## Commands

```bash
pip install -e ".[dev]"                                # install
uvicorn src.transport.app:get_app --factory --host 0.0.0.0 --port 8000  # run server
pytest                                                 # all tests
pytest tests/test_policy.py::test_capability_gating -v # single test
docker compose up --build                              # docker
```

## Architecture

Two layers: **core** (`src/core/`) has no MCP SDK imports; **transport** (`src/transport/`) is the only place importing `FastMCP`.

### Request Flow

```
HTTP POST /mcp (Authorization: Bearer <token>)
  → BearerAuthMiddleware (src/transport/middleware.py)
    → AuthService.resolve(token) → AgentIdentity
      → contextvars.ContextVar("current_agent").set(identity)
        → FastMCP (stateless_http=True) dispatches tool call
          → wrapper function in app.py: current_agent.get() → PolicyEngine.check_tool_call() → plugin.execute()
```

Each tool is registered via `_make_tool_wrapper()` in `src/transport/app.py`, which synthesizes an `inspect.Signature` from the plugin's Pydantic `input_model()` so FastMCP generates the correct JSON schema. This wrapper enforces policy before every execution — there is no bypass path.

### Plugin System

Plugins implement ABCs from `src/plugins/_base.py` (`ToolPlugin`, `ResourcePlugin`, `PromptPlugin`). Each plugin module exposes a `create_plugin(**kwargs)` factory. Registration requires two steps:
1. Add module path to `PLUGIN_MODULES` dict in `src/core/registry.py`
2. Add plugin name to `enabled_plugins` list in `config.yaml`

Resources use `FunctionResource` (not the `@mcp.resource` decorator) to avoid URI parameter validation issues. Prompts use `Prompt.from_function()` then `mcp.add_prompt(prompt_obj)`.

### Policy Engine (`src/core/policy.py`)

Checks on every tool call: tool allowlist, capability gating (`tool.capabilities ⊆ agent.allowed_capabilities`), payload size, rate limit (sliding window), LLM budget (daily cost cap). All denials return a `PolicyDecision` with human-readable `reasons` list.

### LLM Providers

Providers in `src/plugins/llm_query/providers/` use raw `httpx` via `GuardedHttpClient` (not the `openai`/`anthropic` SDK HTTP clients) to ensure egress allowlist enforcement. Input guard (`input_guard.py`) has a 100KB hard limit plus heuristics for repo-paste detection.

## Configuration

`config.yaml` with `${ENV_VAR}` expansion (resolved in `src/core/config.py`). Secrets go in `.env`. Secure defaults: network egress OFF, empty egress allowlist.

## Key Design Rules

- Policy engine checks run on **every** tool call — no bypass path
- All denials include human-readable reasons list
- Network egress is deny-by-default (allowlist empty = no outbound HTTP)
- Core layer (`src/core/`) must never import from `mcp` SDK
- Logging uses `extra={}` dict — avoid keys that collide with LogRecord builtins (`name`, `message`, `asctime`)
- `src/transport/app.py` has no module-level app instance; use `get_app()` factory with `--factory` flag
- Language in code/comments/APIs: English. Requirements doc is in Polish.
