from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from pathlib import Path

import aiohttp
from livekit import agents
from livekit.agents import AgentServer, AgentSession, APIConnectOptions
from livekit.plugins import anam as anam
from livekit.plugins import openai as openai

from showcase_shared.logging import configure_logging
from showcase_shared.settings import Settings, get_settings

from .agent import GREETING, HarborlightAgent
from .business_client import BusinessApiClient
from .telemetry import StatusPublisher
from .tools import build_tools

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def build_avatar_session(settings: Settings) -> anam.AvatarSession | None:
    if not settings.showcase_avatar_enabled:
        return None
    if not settings.anam_avatar_id.strip():
        raise RuntimeError("ANAM_AVATAR_ID is required by the official Anam LiveKit plugin")
    return anam.AvatarSession(
        persona_config=anam.PersonaConfig(
            name="Harborlight Concierge",
            avatarId=settings.anam_avatar_id,
        ),
        api_key=settings.anam_api_key,
    )


settings = get_settings()
configure_logging(settings.log_level)
server = AgentServer(port=settings.agent_health_port)


async def close_session_resources(
    session: AgentSession[None],
    avatar: anam.AvatarSession | None,
    telemetry: StatusPublisher,
    model_http_session: aiohttp.ClientSession | None = None,
) -> None:
    with suppress(Exception):
        await telemetry.emit("session.closed")
    if avatar is not None:
        with suppress(Exception):
            await asyncio.wait_for(avatar.aclose(), timeout=5)
    with suppress(Exception):
        await asyncio.wait_for(session.aclose(), timeout=5)
    if model_http_session is not None:
        with suppress(Exception):
            await asyncio.wait_for(model_http_session.close(), timeout=5)


@server.rtc_session(agent_name=settings.agent_name)
async def harborlight_session(ctx: agents.JobContext) -> None:
    runtime_settings = get_settings()
    runtime_settings.require_live_agent_credentials()
    telemetry = StatusPublisher()
    await telemetry.emit("session.connecting")

    model_http_session = aiohttp.ClientSession(
        proxy=runtime_settings.openai_http_proxy or None,
    )
    session: AgentSession[None] = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model=runtime_settings.openai_realtime_model,
            voice="marin",
            conn_options=APIConnectOptions(
                timeout=runtime_settings.model_connect_timeout_seconds,
                max_retry=3,
                retry_interval=2,
            ),
            http_session=model_http_session,
        )
    )
    model_ready_sent = False
    closed = False
    background_tasks: set[asyncio.Task[None]] = set()

    async def emit_status(event_type: str) -> None:
        try:
            await telemetry.emit(event_type)
        except Exception:
            logger.exception("status_event_publish_failed type=%s", event_type)

    def schedule_status(event_type: str) -> None:
        if closed:
            return
        task = asyncio.create_task(emit_status(event_type))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @session.on("agent_state_changed")
    def on_agent_state_changed(event: object) -> None:
        nonlocal model_ready_sent
        new_state = getattr(event, "new_state", None)
        if new_state in {"idle", "listening", "thinking", "speaking"} and not model_ready_sent:
            model_ready_sent = True
            schedule_status("model.ready")

    @session.on("error")
    def on_session_error(event: object) -> None:
        error = getattr(event, "error", None)
        cause = getattr(error, "error", None)
        logger.error(
            "agent_session_error type=%s cause=%s",
            type(error).__name__,
            type(cause).__name__ if cause is not None else "none",
        )
        schedule_status("model.failed")

    business_client = BusinessApiClient(
        runtime_settings.business_api_url,
        runtime_settings.tool_timeout_seconds,
    )
    tools = build_tools(
        knowledge_directory=ROOT / "knowledge",
        business_client=business_client,
        telemetry=telemetry,
    )
    avatar = build_avatar_session(runtime_settings)

    async def close_resources() -> None:
        nonlocal closed
        if closed:
            return
        closed = True
        if background_tasks:
            await asyncio.gather(*tuple(background_tasks), return_exceptions=True)
        await close_session_resources(session, avatar, telemetry, model_http_session)

    ctx.add_shutdown_callback(close_resources)

    try:
        if avatar is not None:
            await telemetry.emit("avatar.connecting")
            try:
                await avatar.start(
                    session,
                    room=ctx.room,
                    livekit_url=runtime_settings.public_livekit_url,
                    livekit_api_key=runtime_settings.livekit_api_key,
                    livekit_api_secret=runtime_settings.livekit_api_secret,
                )
            except Exception:
                await telemetry.emit("avatar.failed")
                raise

        await session.start(room=ctx.room, agent=HarborlightAgent(tools))
        await telemetry.activate(ctx.room)
        if avatar is not None:
            await telemetry.emit("avatar.ready")
        await telemetry.emit("session.ready")
        await session.generate_reply(instructions=GREETING)
    except Exception:
        logger.exception("voice_session_failed")
        raise


if __name__ == "__main__":
    agents.cli.run_app(server)
