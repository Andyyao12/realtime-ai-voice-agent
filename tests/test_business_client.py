from __future__ import annotations

import httpx
import pytest

from voice_agent.business_client import BusinessApiClient, BusinessServiceError


@pytest.mark.asyncio
async def test_client_maps_not_found_without_leaking_error_body() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": {"debug": "internal-only"}})

    client = BusinessApiClient("http://business.test", transport=httpx.MockTransport(handler))

    assert await client.lookup_reservation("DEMO-9999", "Nobody") == {
        "status": "not_found",
        "code": "RESERVATION_NOT_FOUND",
    }


@pytest.mark.asyncio
async def test_client_translates_network_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("contains-internal-host", request=request)

    client = BusinessApiClient("http://business.test", transport=httpx.MockTransport(handler))

    with pytest.raises(BusinessServiceError, match="Business service is unavailable") as exc_info:
        await client.lookup_reservation("DEMO-2048", "Morgan")

    assert "internal-host" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_client_translates_timeout_without_leaking_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("http://private-service/secret", request=request)

    client = BusinessApiClient("http://business.test", transport=httpx.MockTransport(handler))

    with pytest.raises(BusinessServiceError) as exc_info:
        await client.lookup_reservation("DEMO-2048", "Morgan")

    assert str(exc_info.value) == "Business service is unavailable"
    assert "private-service" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_service_request_returns_typed_public_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/service-requests"
        return httpx.Response(
            201,
            json={
                "request_id": "SR-ABC12345",
                "category": "maintenance",
                "status": "open",
                "requested_time": None,
                "created_at": "2026-08-10T00:00:00+00:00",
            },
        )

    client = BusinessApiClient("http://business.test", transport=httpx.MockTransport(handler))
    result = await client.create_service_request(
        category="maintenance",
        summary="The demo light is not working.",
        requested_time=None,
    )

    assert result["status"] == "ok"
    assert result["request"]["request_id"] == "SR-ABC12345"
