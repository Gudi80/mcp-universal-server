"""Tests for authentication."""
from __future__ import annotations

import pytest

from src.core.auth import AuthService
from src.core.config import AppConfig


def test_resolve_valid_token(sample_config: AppConfig) -> None:
    auth = AuthService(sample_config)
    identity = auth.resolve("token-alpha-secret")
    assert identity is not None
    assert identity.agent_id == "agent-alpha"
    assert identity.tenant_id == "team-a"


def test_resolve_another_valid_token(sample_config: AppConfig) -> None:
    auth = AuthService(sample_config)
    identity = auth.resolve("token-beta-secret")
    assert identity is not None
    assert identity.agent_id == "agent-beta"


def test_resolve_invalid_token(sample_config: AppConfig) -> None:
    auth = AuthService(sample_config)
    identity = auth.resolve("invalid-token")
    assert identity is None


def test_resolve_empty_token(sample_config: AppConfig) -> None:
    auth = AuthService(sample_config)
    identity = auth.resolve("")
    assert identity is None


@pytest.mark.anyio
async def test_401_without_token_integration(sample_config: AppConfig) -> None:
    """Integration test: HTTP request without auth header → 401."""
    from httpx import ASGITransport, AsyncClient
    from src.transport.app import create_app

    app = create_app(config=sample_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_401_bad_token_integration(sample_config: AppConfig) -> None:
    """Integration test: HTTP request with wrong token → 401."""
    from httpx import ASGITransport, AsyncClient
    from src.transport.app import create_app

    app = create_app(config=sample_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
