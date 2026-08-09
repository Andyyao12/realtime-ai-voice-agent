from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from voice_agent.telemetry import TOPIC, StatusPublisher


@pytest.mark.asyncio
async def test_public_event_schema_contains_only_allowlisted_fields() -> None:
    publisher = StatusPublisher()
    participant = Mock(publish_data=AsyncMock())
    room = Mock(local_participant=participant)
    await publisher.emit("session.connecting")
    await publisher.activate(room)
    await publisher.emit("knowledge.matched", duration_ms=12)

    first_payload = json.loads(participant.publish_data.await_args_list[0].args[0])
    assert set(first_payload) == {
        "schema_version",
        "sequence",
        "timestamp",
        "source",
        "type",
        "status",
        "label",
        "duration_ms",
    }
    assert participant.publish_data.await_args_list[0].kwargs == {"reliable": True, "topic": TOPIC}
    assert "session" not in first_payload
    assert "token" not in first_payload


@pytest.mark.asyncio
async def test_rejects_unstructured_event_types() -> None:
    publisher = StatusPublisher()

    with pytest.raises(ValueError, match="Unsupported public event"):
        await publisher.emit("debug.raw-provider-message")


@pytest.mark.asyncio
async def test_model_failure_event_is_public_and_contains_no_provider_detail() -> None:
    publisher = StatusPublisher()

    event = await publisher.emit("model.failed")

    assert event.source == "model"
    assert event.label == "Realtime model unavailable"
    assert "provider" not in event.to_json()


@pytest.mark.asyncio
async def test_activation_does_not_duplicate_concurrent_events() -> None:
    publisher = StatusPublisher()
    participant = Mock(publish_data=AsyncMock())
    room = Mock(local_participant=participant)
    await publisher.emit("session.connecting")

    await asyncio.gather(publisher.activate(room), publisher.emit("model.ready"))

    payloads = [json.loads(call.args[0]) for call in participant.publish_data.await_args_list]
    assert [payload["type"] for payload in payloads] == ["session.connecting", "model.ready"]
