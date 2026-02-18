"""tool_usage prompt — guidelines for safe tool usage."""
from __future__ import annotations

from typing import Any

from src.core.config import AppConfig
from src.core.types import PluginManifest
from src.plugins._base import PromptPlugin

_TEMPLATE = """## Safe Tool Usage Guidelines

You are using tools provided by an MCP server with security policies enforced per-agent.

### General Rules:
1. **Least privilege**: Only call tools you need. Don't explore tools outside your task scope.
2. **Input validation**: Always validate and sanitize inputs before passing to tools.
3. **Error handling**: Handle tool errors gracefully — do not retry failed calls in a tight loop.
4. **Rate awareness**: Be mindful of rate limits. Batch operations when possible.

### LLM Query (`llm.query`) Guidelines:
1. Keep prompts concise. Avoid pasting entire repositories or large codebases.
2. Use the appropriate model for the task (smaller models for simple tasks).
3. Set `max_tokens` to the minimum needed — it affects budget consumption.
4. Never include secrets, API keys, or credentials in prompts.

### Network-Aware Tools:
1. Only configured egress hosts are reachable — check your `about://policies` resource.
2. Timeouts are enforced per-agent. Long-running queries may be terminated.

### Budget Awareness:
1. LLM usage is tracked per-agent with daily cost limits.
2. Check `about://policies` to see your remaining budget.
3. Prefer cheaper models when the task doesn't require advanced reasoning.

{context}"""


class ToolUsagePlugin(PromptPlugin):
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="prompt.tool_usage",
            title="Tool Usage",
            description="Guidelines for safe and efficient tool usage on this MCP server.",
        )

    def prompt_name(self) -> str:
        return "tool_usage"

    def arguments(self) -> list[dict[str, Any]]:
        return [
            {"name": "context", "description": "Additional context or task-specific notes", "required": False},
        ]

    async def render(self, args: dict[str, str]) -> str:
        context = args.get("context", "")
        return _TEMPLATE.format(context=context)


def create_plugin(**kwargs: Any) -> ToolUsagePlugin:
    return ToolUsagePlugin()
