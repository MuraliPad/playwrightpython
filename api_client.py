"""
API Base Client.

All API resource classes inherit from ApiClient.
Uses the authenticated requests.Session from the api_session fixture.
Bearer token is injected once at session creation – no per-call setup.
"""

import requests
from typing import Any, Dict, Optional


class ApiClient:
    """Base HTTP client wrapping an authenticated requests.Session."""

    def __init__(self, session: requests.Session, base_url: str) -> None:
        self._session  = session
        self._base_url = base_url.rstrip("/")

    # ── HTTP Verbs ────────────────────────────────────────────────

    def get(
        self,
        path: str,
        params: Optional[Dict] = None,
        expected_status: int = 200,
    ) -> requests.Response:
        resp = self._session.get(
            f"{self._base_url}{path}",
            params=params,
        )
        self._assert_status(resp, expected_status)
        return resp

    def post(
        self,
        path: str,
        body: Dict,
        expected_status: int = 200,
    ) -> requests.Response:
        resp = self._session.post(
            f"{self._base_url}{path}",
            json=body,
        )
        self._assert_status(resp, expected_status)
        return resp

    def put(
        self,
        path: str,
        body: Dict,
        expected_status: int = 200,
    ) -> requests.Response:
        resp = self._session.put(
            f"{self._base_url}{path}",
            json=body,
        )
        self._assert_status(resp, expected_status)
        return resp

    # ── Response helpers ──────────────────────────────────────────

    @staticmethod
    def _assert_status(resp: requests.Response, expected: int) -> None:
        assert resp.status_code == expected, (
            f"Expected HTTP {expected}, got {resp.status_code}. "
            f"URL: {resp.url}  Body: {resp.text[:300]}"
        )

    @staticmethod
    def parse_json(resp: requests.Response) -> Any:
        return resp.json()

    @staticmethod
    def get_total_count(resp: requests.Response) -> int:
        """
        Extract total record count from common API envelope shapes:
          { "total": N }  |  { "count": N }  |  { "totalCount": N }
          { "items": [...] }  |  root list [...]
        """
        data = resp.json()
        if isinstance(data, dict):
            for key in ("total", "count", "totalCount", "totalElements"):
                if key in data:
                    return int(data[key])
            if "items" in data:
                return len(data["items"])
        if isinstance(data, list):
            return len(data)
        raise ValueError(
            f"Cannot determine count from response. "
            f"Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    @staticmethod
    def assert_response_time(resp: requests.Response, max_ms: int = 3000) -> None:
        elapsed = resp.elapsed.total_seconds() * 1000
        assert elapsed <= max_ms, \
            f"Response time {elapsed:.0f}ms exceeded limit of {max_ms}ms"
