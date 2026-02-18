# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mcp-universal-server** — a remote MCP (Model Context Protocol) server using Streamable HTTP transport, designed for multiple Claude Code agents on a LAN/VPN. Runs on a single Proxmox VM. Priority: security (hard guardrails), multi-tenancy, audit.

Full requirements spec: `req/mcp.md`

## Tech Stack

- Python 3.11+, FastAPI + Uvicorn, MCP Python SDK (Streamable HTTP, NOT SSE)
- Pydantic for config and tool input validation
- pytest for tests
- Structured JSON logging to stdout
- Docker deployment (Dockerfile + docker-compose.yml)

## Architecture

Two-layer separation: **core** (business logic) vs **transport** (FastAPI `/mcp` adapter).

### Core Layer (`src/core/`)
- **Plugin registry/loader** — central registration, config-driven enable/disable
- **Policy engine** — middleware on every tool-call: allowlists per agent/tenant, capability gating, network egress allowlist, rate/size/timeout limits, LLM budget tracking, secret/PII redaction in logs, deny reasons
- **Auth** — Bearer token → (agent_id, tenant_id) mapping from config file; reject unauthenticated requests
- **Audit** — structured logging of all tool calls and policy decisions
- **Config** — Pydantic models for all configuration

### Plugin System (`src/plugins/`)
Each plugin is a module with a **manifest** (name, title, description, capabilities like `network:outbound`, `llm:query`, `fs:read`, `db:read`) and a **handler**. Plugins provide MCP tools, resources, and prompts.

Built-in plugins:
- **Tools:** `core.echo`, `core.sum`, `llm.query` (LLM router)
- **Resources:** `about://server`, `about://policies` (effective config without secrets)
- **Prompts:** `review_pr`, `tool_usage`

### LLM Router (`src/plugins/llm_query/providers/`)
Common provider interface with implementations: `openai.py`, `anthropic.py`, `local.py`. Per-provider model allowlist in config. Egress allowlist must include provider domains. Input size limits with heuristic to block "repo paste" attempts.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run server
uvicorn src.transport.app:get_app --factory --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run single test
pytest tests/test_policy.py::test_capability_gating -v

# Docker
docker compose up --build
```

## Configuration

- `config.yaml` (or JSON) + ENV overrides for secrets (API keys etc.)
- `.env.example` for reference
- Secure defaults: network egress OFF, only `core.echo` and `core.sum` enabled for the example agent

### Connecting Claude Code

```bash
claude mcp add --transport http <server-url>/mcp --header "Authorization: Bearer <token>"
```

## Tests

```bash
pytest                                              # all tests
pytest tests/test_policy.py -v                      # single file
pytest tests/test_policy.py::test_capability_gating -v  # single test
```

Required test coverage:
- Policy engine: allow/deny on tool allowlists
- Egress: deny if host not on allowlist
- llm.query: deny if model not on allowlist or budget exhausted
- Auth: 401 without token

## Key Design Rules

- Policy engine checks run on **every** tool call — no bypass path
- All denials include a list of human-readable reasons
- Network egress is deny-by-default (allowlist empty = no outbound HTTP)
- LLM budgets (max_tokens_per_request, max_cost_per_day) are tracked per-agent
- Secrets and PII must be redacted from all log output
- MCP HTTP responses must never contain log output — logs go through the JSON logger only
- Provider API key missing → user-friendly error, never crash
- Language in code/comments/APIs: English. Requirements doc is in Polish.
