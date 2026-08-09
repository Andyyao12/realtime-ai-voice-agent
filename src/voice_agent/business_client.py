from __future__ import annotations

from typing import Any

import httpx


class BusinessServiceError(RuntimeError):
    pass


class BusinessApiClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=min(2.0, timeout_seconds))
        self.transport = transport

    async def lookup_reservation(self, reference: str, last_name: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.get(
                    f"{self.base_url}/v1/reservations/{reference}",
                    params={"last_name": last_name},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise BusinessServiceError("Business service is unavailable") from exc
        if response.status_code == 404:
            return {"status": "not_found", "code": "RESERVATION_NOT_FOUND"}
        if response.status_code == 400:
            return {"status": "invalid_request", "code": "INVALID_LOOKUP"}
        if response.status_code != 200:
            raise BusinessServiceError("Business service returned an unexpected response")
        return {"status": "ok", "reservation": response.json()}

    async def create_service_request(
        self,
        *,
        category: str,
        summary: str,
        requested_time: str | None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.post(
                    f"{self.base_url}/v1/service-requests",
                    json={
                        "category": category,
                        "summary": summary,
                        "requested_time": requested_time,
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise BusinessServiceError("Business service is unavailable") from exc
        if response.status_code == 422:
            return {"status": "invalid_request", "code": "INVALID_SERVICE_REQUEST"}
        if response.status_code != 201:
            raise BusinessServiceError("Business service returned an unexpected response")
        return {"status": "ok", "request": response.json()}
