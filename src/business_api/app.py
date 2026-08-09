from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from showcase_shared.logging import configure_logging
from showcase_shared.settings import Settings, get_settings

from . import database
from .models import (
    ErrorResponse,
    HealthResponse,
    ReservationResponse,
    ServiceRequestCreate,
    ServiceRequestResponse,
)

REFERENCE_PATTERN = re.compile(r"^DEMO-[0-9]{4}$")
LAST_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z -]{0,49}$")


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize(runtime_settings.database_url)
        yield

    app = FastAPI(
        title="Showcase Mock Business API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        if request.url.path.startswith("/v1/reservations/"):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_LOOKUP",
                        "message": "Invalid reservation lookup fields.",
                    }
                },
            )
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "INVALID_SERVICE_REQUEST",
                    "message": "Invalid service request fields.",
                }
            },
        )

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        database.initialize(runtime_settings.database_url)
        return HealthResponse(status="ok", database="ready")

    @app.get(
        "/v1/reservations/{reference}",
        response_model=ReservationResponse,
        responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["reservations"],
    )
    def reservation(
        reference: str,
        last_name: str = Query(min_length=1, max_length=50),
    ) -> ReservationResponse:
        normalized_reference = reference.strip().upper()
        normalized_last_name = last_name.strip()
        if not REFERENCE_PATTERN.fullmatch(normalized_reference) or not LAST_NAME_PATTERN.fullmatch(
            normalized_last_name
        ):
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_LOOKUP", "message": "Invalid reservation lookup fields."},
            )
        record = database.find_reservation(
            runtime_settings.database_url,
            normalized_reference,
            normalized_last_name,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RESERVATION_NOT_FOUND", "message": "Reservation not found."},
            )
        return ReservationResponse.model_validate(record)

    @app.post(
        "/v1/service-requests",
        response_model=ServiceRequestResponse,
        status_code=201,
        tags=["service requests"],
    )
    def service_request(payload: ServiceRequestCreate) -> ServiceRequestResponse:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        record = database.create_request(
            runtime_settings.database_url,
            request_id=f"SR-{uuid4().hex[:8].upper()}",
            category=payload.category.value,
            summary=payload.summary.strip(),
            requested_time=payload.requested_time.strip() if payload.requested_time else None,
            created_at=created_at,
        )
        return ServiceRequestResponse.model_validate(record)

    return app


app = create_app()
