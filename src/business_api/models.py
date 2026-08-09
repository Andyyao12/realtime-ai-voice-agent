from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceCategory(StrEnum):
    HOUSEKEEPING = "housekeeping"
    MAINTENANCE = "maintenance"
    CONCIERGE = "concierge"
    BILLING = "billing"


class HealthResponse(BaseModel):
    status: str
    database: str


class ReservationResponse(BaseModel):
    reference: str
    status: str
    room_type: str
    check_in: date
    check_out: date
    breakfast_included: bool


class ServiceRequestCreate(BaseModel):
    category: ServiceCategory
    summary: str = Field(min_length=5, max_length=300)
    requested_time: str | None = Field(default=None, max_length=80)


class ServiceRequestResponse(BaseModel):
    request_id: str
    category: ServiceCategory
    status: str
    requested_time: str | None
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail
