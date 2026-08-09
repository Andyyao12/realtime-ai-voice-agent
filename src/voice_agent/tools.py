from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from livekit.agents import function_tool

from .business_client import BusinessApiClient, BusinessServiceError
from .knowledge import MarkdownKnowledgeBase
from .telemetry import StatusPublisher


def build_tools(
    *,
    knowledge_directory: str | Path,
    business_client: BusinessApiClient,
    telemetry: StatusPublisher,
) -> list[Any]:
    knowledge = MarkdownKnowledgeBase.from_directory(knowledge_directory)

    @function_tool(
        name="search_knowledge",
        description=(
            "Search the verified Harborlight Hotel public knowledge base. Always use this before "
            "answering about breakfast, checkout, Wi-Fi, cancellation, parking, or hotel services."
        ),
    )
    async def search_knowledge(query: str) -> dict[str, Any]:
        """Search verified public hotel information.

        Args:
            query: The guest's concise question.
        """
        started = time.perf_counter()
        await telemetry.emit("knowledge.searching")
        match = knowledge.search(query)
        duration = round((time.perf_counter() - started) * 1000)
        if match is None:
            await telemetry.emit("knowledge.no_match", duration_ms=duration)
            return {"status": "no_match"}
        await telemetry.emit("knowledge.matched", duration_ms=duration)
        return {
            "status": "matched",
            "source": match.source_id,
            "title": match.title,
            "answer": match.answer,
        }

    @function_tool(
        name="lookup_reservation",
        description=(
            "Look up a fictional demo reservation using both its DEMO-0000 reference "
            "and guest last name. "
            "This tool never changes a reservation."
        ),
    )
    async def lookup_reservation(reference: str, last_name: str) -> dict[str, Any]:
        """Look up one demo reservation.

        Args:
            reference: Reservation reference in DEMO-0000 format.
            last_name: Guest family name.
        """
        started = time.perf_counter()
        await telemetry.emit("tool.lookup.started")
        try:
            result = await business_client.lookup_reservation(
                reference.strip().upper(), last_name.strip()
            )
        except BusinessServiceError:
            await telemetry.emit("tool.failed")
            return {"status": "unavailable", "code": "BUSINESS_SERVICE_UNAVAILABLE"}
        await telemetry.emit(
            "tool.lookup.completed",
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        return result

    @function_tool(
        name="create_service_request",
        description=(
            "Create a fictional hotel service request after the guest confirms the category "
            "and summary. "
            "Allowed categories are housekeeping, maintenance, concierge, and billing."
        ),
    )
    async def create_service_request(
        category: str,
        summary: str,
        requested_time: str | None = None,
    ) -> dict[str, Any]:
        """Create one demo service request.

        Args:
            category: One allowed service category.
            summary: A short description confirmed by the guest.
            requested_time: Optional requested time in the guest's own words.
        """
        started = time.perf_counter()
        await telemetry.emit("tool.request.started")
        try:
            result = await business_client.create_service_request(
                category=category.strip().lower(),
                summary=summary.strip(),
                requested_time=requested_time.strip() if requested_time else None,
            )
        except BusinessServiceError:
            await telemetry.emit("tool.failed")
            return {"status": "unavailable", "code": "BUSINESS_SERVICE_UNAVAILABLE"}
        await telemetry.emit(
            "tool.request.completed",
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        return result

    return [search_knowledge, lookup_reservation, create_service_request]
