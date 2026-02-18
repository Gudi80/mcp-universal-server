# mcp-universal-server

Remote MCP (Model Context Protocol) server using Streamable HTTP transport, designed for multiple Claude Code agents on a LAN/VPN. Runs on a single Proxmox VM.

Priorities: security (hard guardrails), multi-tenancy, audit.

## Quick Start

### Local

```bash
# Install
pip install -e ".[dev]"

# Set tokens
export AGENT_ALPHA_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export AGENT_BETA_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Run server
uvicorn src.transport.app:get_app --factory --host 0.0.0.0 --port 8000
```

### Docker

```bash
cp .env.example .env
# Edit .env with your tokens and API keys
docker compose up --build
```

### systemd (on Proxmox VM)

```ini
# /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Universal Server
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-universal-server
EnvironmentFile=/opt/mcp-universal-server/.env
ExecStart=/opt/mcp-universal-server/.venv/bin/uvicorn src.transport.app:get_app --factory --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcp-server
```

## Connecting Claude Code

```bash
claude mcp add --transport http http://<host>:8000/mcp \
  --header "Authorization: Bearer <your-agent-token>"
```

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Configuration

All configuration lives in `config.yaml` with ENV variable expansion (`${VAR}`). Secrets should be set via environment variables or `.env` file.

### Agent Configuration

Each agent gets a bearer token, a set of allowed tools, capabilities, and limits:

```yaml
agents:
  my-agent:
    token: "${MY_AGENT_TOKEN}"
    tenant_id: "my-team"
    allowed_tools:
      - "core.echo"
      - "core.sum"
    allowed_capabilities: []       # empty = no network, no LLM
    egress_allowlist: []           # empty = no outbound HTTP
    rate_limit: 60                 # requests per minute
    max_cost_per_day: 10.0         # USD daily LLM budget
```

To enable LLM queries, add the required capabilities and egress hosts:

```yaml
agents:
  llm-agent:
    token: "${LLM_AGENT_TOKEN}"
    allowed_tools: ["core.echo", "core.sum", "llm.query"]
    allowed_capabilities:
      - "network:outbound"
      - "llm:query"
    egress_allowlist:
      - "api.openai.com"
      - "api.anthropic.com"
    max_tokens_per_request: 8192
    max_cost_per_day: 25.0
```

### Egress Allowlist

Network egress is **deny-by-default**. To allow LLM providers:

```yaml
egress_allowlist:
  - "api.openai.com"      # OpenAI
  - "api.anthropic.com"   # Anthropic
  - "localhost"            # Ollama (local)
```

## Built-in Plugins

### Tools
| Name | Description | Capabilities Required |
|------|-------------|----------------------|
| `core.echo` | Returns input text | none |
| `core.sum` | Sums two numbers | none |
| `llm.query` | Routes queries to LLM providers | `network:outbound`, `llm:query` |

### Resources
| URI | Description |
|-----|-------------|
| `about://server` | Server name, version, description |
| `about://policies` | Effective config for requesting agent (secrets redacted) |

### Prompts
| Name | Description |
|------|-------------|
| `review_pr` | Structured code review template |
| `tool_usage` | Safe tool usage guidelines |

## Adding Plugins

Create a new module under `src/plugins/my_plugin/plugin.py`:

```python
from src.plugins._base import ToolPlugin, ToolContext
from src.core.types import PluginManifest, Capability
from pydantic import BaseModel, Field

class MyInput(BaseModel):
    arg: str = Field(description="My argument")

class MyPlugin(ToolPlugin):
    def manifest(self):
        return PluginManifest(
            name="my.tool",
            title="My Tool",
            description="Does something.",
            capabilities=frozenset(),
        )

    def input_model(self):
        return MyInput

    async def execute(self, ctx, params):
        return f"Result: {params.arg}"

def create_plugin(**kwargs):
    return MyPlugin()
```

Register it in `src/core/registry.py` (`PLUGIN_MODULES` dict) and add to `enabled_plugins` in `config.yaml`.

## Testing

```bash
pytest                                              # all tests
pytest tests/test_policy.py -v                      # single file
pytest tests/test_policy.py::test_capability_gating -v  # single test
```

## Architecture

```
HTTP request (Authorization: Bearer <token>)
  -> BearerAuthMiddleware -> AuthService.resolve() -> AgentIdentity
    -> ContextVar("current_agent").set(identity)
      -> MCP SDK dispatches tool call
        -> wrapper: current_agent.get() -> PolicyEngine -> plugin.execute()
```

Policy engine runs on **every** tool call with no bypass path. Checks:
1. Tool allowlist per agent
2. Capability gating (tool capabilities subset of agent capabilities)
3. Payload size limits
4. Rate limits (sliding window)
5. LLM budget (daily cost cap)

All denials include human-readable reasons.

## File Structure

```
mcp-universal-server/
├── pyproject.toml
├── config.yaml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── README.md
├── CLAUDE.md
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── core/
│   │   ├── types.py          # AgentIdentity, PluginManifest, PolicyDecision, Capability
│   │   ├── config.py         # Pydantic models + YAML/ENV loader
│   │   ├── auth.py           # Bearer token -> AgentIdentity
│   │   ├── policy.py         # Policy engine
│   │   ├── egress.py         # GuardedHttpClient
│   │   ├── budget.py         # Per-agent LLM cost tracker
│   │   ├── rate_limit.py     # Rate + concurrency limiters
│   │   ├── redact.py         # Secret/PII redaction
│   │   ├── audit.py          # JSON logger setup
│   │   └── registry.py       # Plugin loader
│   ├── transport/
│   │   ├── app.py            # FastAPI + FastMCP mount
│   │   └── middleware.py     # Bearer auth middleware + ContextVar
│   └── plugins/
│       ├── _base.py          # ABC: ToolPlugin, ResourcePlugin, PromptPlugin
│       ├── core_echo/
│       ├── core_sum/
│       ├── llm_query/
│       │   ├── plugin.py
│       │   ├── input_guard.py
│       │   └── providers/    # openai, anthropic, local
│       ├── about_server/
│       ├── about_policies/
│       ├── prompt_review_pr/
│       └── prompt_tool_usage/
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_policy.py
    ├── test_egress.py
    ├── test_budget.py
    ├── test_llm_query.py
    ├── test_plugins.py
    ├── test_redact.py
    └── test_integration.py
```
