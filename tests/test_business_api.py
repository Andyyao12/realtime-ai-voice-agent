from __future__ import annotations

from fastapi.testclient import TestClient

from business_api.app import create_app
from showcase_shared.settings import Settings


def test_health_and_seeded_reservation(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json() == {"status": "ok", "database": "ready"}
        response = client.get("/v1/reservations/DEMO-2048", params={"last_name": "Morgan"})

    assert response.status_code == 200
    assert response.json() == {
        "reference": "DEMO-2048",
        "status": "confirmed",
        "room_type": "Harbor View King",
        "check_in": "2026-09-14",
        "check_out": "2026-09-17",
        "breakfast_included": True,
    }


def test_reservation_lookup_does_not_enumerate_by_reference(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/reservations/DEMO-2048", params={"last_name": "Wrong"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESERVATION_NOT_FOUND"


def test_invalid_lookup_has_stable_error(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/reservations/not-valid", params={"last_name": "123"})

    assert response.status_code == 400
    assert response.json() == {
        "detail": {"code": "INVALID_LOOKUP", "message": "Invalid reservation lookup fields."}
    }


def test_service_request_is_persisted_with_public_response(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/v1/service-requests",
            json={
                "category": "housekeeping",
                "summary": "Please bring two extra towels.",
                "requested_time": "after 7 PM",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["request_id"].startswith("SR-")
    assert payload["category"] == "housekeeping"
    assert payload["status"] == "open"
    assert "summary" not in payload


def test_invalid_service_request_has_stable_error(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/v1/service-requests",
            json={"category": "unsupported", "summary": "x"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "INVALID_SERVICE_REQUEST",
            "message": "Invalid service request fields.",
        }
    }
