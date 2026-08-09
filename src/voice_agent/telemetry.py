from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

TOPIC = "showcase.status.v1"
ALLOWED_EVENTS = {
    "session.connecting": ("runtime", "connecting", "Connecting session"),
    "session.ready": ("runtime", "ready", "Session ready"),
    "session.closed": ("runtime", "closed", "Session closed"),
    "model.ready": ("model", "ready", "Realtime model ready"),
    "model.failed": ("model", "failed", "Realtime model unavailable"),
    "avatar.connecting": ("avatar", "connecting", "Loading digital human"),
    "avatar.ready": ("avatar", "ready", "Digital human ready"),
    "avatar.failed": ("avatar", "failed", "Digital human unavailable"),
    "knowledge.searching": ("knowledge", "running", "Searching knowledge"),
    "knowledge.matched": ("knowledge", "ok", "Knowledge found"),
    "knowledge.no_match": ("knowledge", "no_match", "No verified answer"),
    "tool.lookup.started": ("tool", "running", "Checking reservation"),
    "tool.lookup.completed": ("tool", "ok", "Reservation lookup complete"),
    "tool.request.started": ("tool", "running", "Creating service request"),
    "tool.request.completed": ("tool", "ok", "Service request created"),
    "tool.failed": ("tool", "failed", "Business service unavailable"),
}


@dataclass(frozen=True, slots=True)
class StatusEvent:
    schema_version: int
    sequence: int
    timestamp: str
    source: str
    type: str
    status: str
    label: str
    duration_ms: int | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=True, separators=(",", ":"))


class StatusPublisher:
    def __init__(self) -> None:
        self._participant: Any | None = None
        self._sequence = 0
        self._lock = asyncio.Lock()
        self.events: list[StatusEvent] = []

    async def activate(self, room: Any) -> None:
        async with self._lock:
            participant = room.local_participant
            for event in self.events:
                await participant.publish_data(event.to_json(), reliable=True, topic=TOPIC)
            self._participant = participant

    async def emit(self, event_type: str, *, duration_ms: int | None = None) -> StatusEvent:
        async with self._lock:
            if event_type not in ALLOWED_EVENTS:
                raise ValueError(f"Unsupported public event type: {event_type}")
            source, status, label = ALLOWED_EVENTS[event_type]
            self._sequence += 1
            event = StatusEvent(
                schema_version=1,
                sequence=self._sequence,
                timestamp=datetime.now(UTC).isoformat(timespec="milliseconds"),
                source=source,
                type=event_type,
                status=status,
                label=label,
                duration_ms=duration_ms,
            )
            self.events.append(event)
            if self._participant is not None:
                await self._participant.publish_data(event.to_json(), reliable=True, topic=TOPIC)
            return event
