"""Plugin loader and registry — config-driven enable/disable."""
from __future__ import annotations

import importlib
import logging
from typing import Any

from src.core.config import AppConfig
from src.plugins._base import PromptPlugin, ResourcePlugin, ToolPlugin

logger = logging.getLogger("mcp_server")

# Map plugin names to their module paths
PLUGIN_MODULES: dict[str, str] = {
    "core.echo": "src.plugins.core_echo.plugin",
    "core.sum": "src.plugins.core_sum.plugin",
    "llm.query": "src.plugins.llm_query.plugin",
    "about.server": "src.plugins.about_server.plugin",
    "about.policies": "src.plugins.about_policies.plugin",
    "instructions.agent": "src.plugins.instructions_agent.plugin",
    "prompt.review_pr": "src.plugins.prompt_review_pr.plugin",
    "prompt.tool_usage": "src.plugins.prompt_tool_usage.plugin",
}


class PluginRegistry:
    """Loads and holds all enabled plugin instances."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolPlugin] = {}
        self.resources: dict[str, ResourcePlugin] = {}
        self.prompts: dict[str, PromptPlugin] = {}

    def load(self, config: AppConfig, **kwargs: Any) -> None:
        """Load all enabled plugins from config."""
        for plugin_name in config.enabled_plugins:
            module_path = PLUGIN_MODULES.get(plugin_name)
            if module_path is None:
                logger.warning("Unknown plugin: %s", plugin_name)
                continue
            try:
                module = importlib.import_module(module_path)
                factory = getattr(module, "create_plugin")
                plugin = factory(config=config, **kwargs)

                if isinstance(plugin, ToolPlugin):
                    self.tools[plugin.manifest().name] = plugin
                    logger.info("Loaded tool plugin: %s", plugin_name)
                elif isinstance(plugin, ResourcePlugin):
                    self.resources[plugin.uri()] = plugin
                    logger.info("Loaded resource plugin: %s", plugin_name)
                elif isinstance(plugin, PromptPlugin):
                    self.prompts[plugin.prompt_name()] = plugin
                    logger.info("Loaded prompt plugin: %s", plugin_name)
                else:
                    logger.warning("Plugin %s has unknown type", plugin_name)
            except Exception:
                logger.exception("Failed to load plugin: %s", plugin_name)
