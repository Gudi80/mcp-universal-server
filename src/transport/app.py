"""FastAPI app + FastMCP mount + wiring."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.core.audit import setup_logging
from src.core.auth import AuthService
from src.core.config import AppConfig, load_config
from src.core.policy import PolicyEngine
from src.core.registry import PluginRegistry
from src.core.types import PolicyDecision
from src.plugins._base import ToolContext, ToolPlugin
from src.transport.middleware import BearerAuthMiddleware, current_agent

logger = logging.getLogger("mcp_server")


def _make_tool_wrapper(
    plugin: ToolPlugin,
    policy: PolicyEngine,
) -> Any:
    """Build a wrapper function for a tool plugin that enforces policy.

    The wrapper reads AgentIdentity from ContextVar, runs policy check,
    then delegates to plugin.execute() if allowed.
    """
    manifest = plugin.manifest()
    input_model = plugin.input_model()

    # Get field info from the input model for building the wrapper signature
    model_fields = input_model.model_fields

    # Build the wrapper with **kwargs so FastMCP generates schema from the input model
    async def tool_wrapper(**kwargs: Any) -> str:
        identity = current_agent.get()
        if identity is None:
            return json.dumps({"error": "Not authenticated"})

        payload_size = len(json.dumps(kwargs))
        decision = policy.check_tool_call(identity, manifest, payload_size)

        if not decision.allowed:
            logger.warning(
                "Tool call denied",
                extra={
                    "agent_id": identity.agent_id,
                    "tool": manifest.name,
                    "reasons": decision.reasons,
                },
            )
            return json.dumps({
                "error": "Policy denied",
                "reasons": decision.reasons,
            })

        try:
            params = input_model.model_validate(kwargs)
            ctx = ToolContext(identity=identity, raw_arguments=kwargs)
            result = await plugin.execute(ctx, params)
            logger.info(
                "Tool call success",
                extra={
                    "agent_id": identity.agent_id,
                    "tool": manifest.name,
                },
            )
            return result
        except Exception as exc:
            logger.exception(
                "Tool execution error",
                extra={
                    "agent_id": identity.agent_id,
                    "tool": manifest.name,
                },
            )
            return json.dumps({"error": str(exc)})

    # Copy the input model's schema to the wrapper so FastMCP generates correct JSON schema.
    # We do this by giving the wrapper the right annotations and defaults.
    import inspect

    params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for field_name, field_info in model_fields.items():
        default = field_info.default if field_info.default is not None else inspect.Parameter.empty
        params.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=field_info.annotation,
            )
        )

    # Remove 'self' — FastMCP doesn't need it
    params = params[1:]

    # Apply annotations and signature to the wrapper
    tool_wrapper.__annotations__ = {
        field_name: field_info.annotation
        for field_name, field_info in model_fields.items()
    }
    tool_wrapper.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    tool_wrapper.__name__ = manifest.name.replace(".", "_")
    tool_wrapper.__doc__ = manifest.description

    return tool_wrapper


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Create and wire the FastAPI application."""
    if config is None:
        config = load_config()

    # Setup logging with redaction
    setup_logging(config.redact_patterns)

    # Core services
    auth_service = AuthService(config)
    policy_engine = PolicyEngine(config)

    # Load plugins
    registry = PluginRegistry()
    registry.load(config=config, policy_engine=policy_engine)

    # Create FastMCP instance — streamable_http_path="" because we mount at /mcp
    mcp = FastMCP(
        name=config.server.name,
        instructions=config.server.description,
        stateless_http=True,
        streamable_http_path="/",
    )

    # Register tool plugins as MCP tools via wrappers
    for tool_name, plugin in registry.tools.items():
        manifest = plugin.manifest()
        wrapper = _make_tool_wrapper(plugin, policy_engine)
        mcp.add_tool(
            wrapper,
            name=manifest.name,
            title=manifest.title,
            description=manifest.description,
        )
        logger.info("Registered MCP tool: %s", manifest.name)

    # Register resource plugins using FunctionResource (avoids decorator param mismatch)
    from mcp.server.fastmcp.resources.types import FunctionResource

    for uri, resource_plugin in registry.resources.items():
        _plugin = resource_plugin  # closure capture

        def _make_reader(p: Any) -> Any:
            async def _read() -> str:
                identity = current_agent.get()
                return await p.read(identity)
            return _read

        res = FunctionResource(
            uri=uri,
            name=_plugin.manifest().name,
            description=_plugin.manifest().description,
            fn=_make_reader(_plugin),
        )
        mcp.add_resource(res)

    # Register prompt plugins
    from mcp.server.fastmcp.prompts import Prompt

    for prompt_name, prompt_plugin in registry.prompts.items():
        p_manifest = prompt_plugin.manifest()

        def _make_renderer(p: Any) -> Any:
            async def _render(**kwargs: str) -> str:
                return await p.render(kwargs)
            return _render

        prompt_obj = Prompt.from_function(
            fn=_make_renderer(prompt_plugin),
            name=prompt_plugin.prompt_name(),
            description=p_manifest.description,
        )
        mcp.add_prompt(prompt_obj)

    # Build the MCP Starlette sub-app (initializes session_manager)
    mcp_app = mcp.streamable_http_app()

    # Wire lifespan: parent app must start/stop the MCP session manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[override]
        async with mcp.session_manager.run():
            yield

    # Create FastAPI app with MCP lifespan
    app = FastAPI(
        title=config.server.name,
        version=config.server.version,
        lifespan=lifespan,
    )

    # Add auth middleware
    app.add_middleware(BearerAuthMiddleware, auth_service=auth_service)

    # Health endpoint
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Mount MCP sub-app at /mcp (streamable_http_path="" avoids double /mcp/mcp)
    app.mount("/mcp", mcp_app)

    logger.info(
        "Server initialized",
        extra={
            "server_name": config.server.name,
            "tools": list(registry.tools.keys()),
            "resources": list(registry.resources.keys()),
            "prompts": list(registry.prompts.keys()),
        },
    )

    return app


def get_app() -> FastAPI:
    """App factory for uvicorn: `uvicorn src.transport.app:get_app --factory`."""
    return create_app()
