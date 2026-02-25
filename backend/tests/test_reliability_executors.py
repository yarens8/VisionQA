import os
import sys
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.exc import OperationalError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from executors.api.api_executor import APIExecutor
from executors.database.db_executor import DatabaseExecutor


def _httpx_response(status_code: int, body: str = "{}", content_type: str = "application/json"):
    request = httpx.Request("GET", "http://example.com")
    return httpx.Response(
        status_code=status_code,
        content=body.encode("utf-8"),
        headers={"content-type": content_type},
        request=request,
    )


@pytest.mark.asyncio
async def test_api_executor_retries_on_server_error_then_succeeds():
    executor = APIExecutor(max_retries=1, retry_delay_sec=0.0)
    try:
        executor.client.request = AsyncMock(
            side_effect=[_httpx_response(500), _httpx_response(200)]
        )

        result = await executor.execute_step("GET", "http://example.com")

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["attempts"] == 2
    finally:
        await executor.close()


@pytest.mark.asyncio
async def test_api_executor_retries_on_transport_error_then_succeeds():
    executor = APIExecutor(max_retries=1, retry_delay_sec=0.0)
    try:
        executor.client.request = AsyncMock(
            side_effect=[
                httpx.ConnectError("temporary network issue"),
                _httpx_response(200),
            ]
        )

        result = await executor.execute_step("GET", "http://example.com")

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["attempts"] == 2
    finally:
        await executor.close()


class _FakeResult:
    returns_rows = True

    def all(self):
        return [type("Row", (), {"_mapping": {"ok": 1}})()]


class _FakeConn:
    def __init__(self, should_fail: bool):
        self.should_fail = should_fail

    def __enter__(self):
        if self.should_fail:
            raise OperationalError("SELECT 1", {}, Exception("db temporarily unavailable"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, *_args, **_kwargs):
        return _FakeResult()


def test_db_executor_retries_on_operational_error_then_succeeds():
    executor = DatabaseExecutor("sqlite:///:memory:", max_retries=1, retry_delay_sec=0.0)

    attempts = {"n": 0}

    def fake_connect():
        attempts["n"] += 1
        return _FakeConn(should_fail=attempts["n"] == 1)

    executor.engine.connect = fake_connect  # type: ignore[assignment]
    result = executor.execute_query("SELECT 1 as ok")

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["data"][0]["ok"] == 1

