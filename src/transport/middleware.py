"""Starlette middleware: Bearer token → ContextVar for current agent."""
from __future__ import annotations

import contextvars
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.auth import AuthService
from src.core.types import AgentIdentity

current_agent: contextvars.ContextVar[AgentIdentity | None] = contextvars.ContextVar(
    "current_agent", default=None
)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Extract Bearer token from Authorization header and set current_agent ContextVar.

    Allows /health through without auth. All other paths require valid token.
    """

    def __init__(self, app: Any, auth_service: AuthService) -> None:
        super().__init__(app)
        self._auth = auth_service

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Allow health check without auth
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header[7:]  # Strip "Bearer "
        identity = self._auth.resolve(token)
        if identity is None:
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=401,
            )

        current_agent.set(identity)
        return await call_next(request)
