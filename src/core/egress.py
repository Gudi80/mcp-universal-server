"""Guarded HTTP client: httpx wrapper enforcing egress allowlist."""
from __future__ import annotations

from urllib.parse import urlparse

import httpx


class EgressDeniedError(Exception):
    """Raised when an outbound HTTP request targets a host not on the allowlist."""

    def __init__(self, host: str, allowlist: list[str]) -> None:
        self.host = host
        self.allowlist = allowlist
        super().__init__(
            f"Egress denied: host '{host}' is not on the allowlist {allowlist}"
        )


class GuardedHttpClient:
    """httpx.AsyncClient wrapper that enforces an egress host allowlist.

    Every outbound request is checked before being sent.
    """

    def __init__(self, allowlist: list[str], timeout: float = 30.0) -> None:
        self._allowlist = [h.lower() for h in allowlist]
        self._client = httpx.AsyncClient(timeout=timeout)

    def _check(self, url: str) -> None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in self._allowlist:
            raise EgressDeniedError(host, self._allowlist)

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        self._check(url)
        return await self._client.request(method, url, **kwargs)

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        self._check(url)
        return await self._client.post(url, **kwargs)

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        self._check(url)
        return await self._client.get(url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()
