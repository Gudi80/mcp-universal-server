"""Integration tests: full HTTP round-trip through auth → policy → tool → response."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import AppConfig
from src.transport.app import create_app


@pytest.mark.anyio
async def test_health_endpoint(sample_config: AppConfig) -> None:
    app = create_app(config=sample_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_no_auth_required(sample_config: AppConfig) -> None:
    """Health endpoint should work without any auth header."""
    app = create_app(config=sample_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
