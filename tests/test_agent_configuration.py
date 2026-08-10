from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from showcase_shared.settings import Settings
from voice_agent import entrypoint
from voice_agent.agent import PUBLIC_INSTRUCTIONS


def test_prompt_requires_tools_and_refuses_unverified_answers() -> None:
    assert "Use search_knowledge" in PUBLIC_INSTRUCTIONS
    assert "Never invent" in PUBLIC_INSTRUCTIONS
    assert "fictional demo data" in PUBLIC_INSTRUCTIONS


def test_avatar_can_be_disabled_for_credential_free_ci() -> None:
    settings = Settings(_env_file=None, showcase_avatar_enabled=False)

    assert entrypoint.build_avatar_session(settings) is None


def test_avatar_is_opt_in_by_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.showcase_avatar_enabled is False
    assert entrypoint.build_avatar_session(settings) is None


def test_model_connect_timeout_is_bounded() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, model_connect_timeout_seconds=61)


def test_openai_proxy_rejects_non_http_urls() -> None:
    with pytest.raises(ValueError, match="OPENAI_HTTP_PROXY"):
        Settings(_env_file=None, openai_http_proxy="file:///tmp/proxy")


def test_official_anam_plugin_receives_only_public_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    avatar_factory = Mock(return_value=Mock())
    persona_factory = Mock(return_value=Mock())
    monkeypatch.setattr(entrypoint.anam, "AvatarSession", avatar_factory)
    monkeypatch.setattr(entrypoint.anam, "PersonaConfig", persona_factory)
    settings = Settings(
        _env_file=None,
        showcase_avatar_enabled=True,
        anam_api_key="test-anam-key",
        anam_avatar_id="avatar-demo",
    )

    result = entrypoint.build_avatar_session(settings)

    assert result is avatar_factory.return_value
    persona_factory.assert_called_once_with(name="Harborlight Concierge", avatarId="avatar-demo")
    avatar_factory.assert_called_once_with(
        persona_config=persona_factory.return_value,
        api_key="test-anam-key",
    )


def test_missing_avatar_id_fails_before_network_start() -> None:
    settings = Settings(
        _env_file=None,
        showcase_avatar_enabled=True,
        anam_api_key="test-anam-key",
        anam_avatar_id="",
    )

    with pytest.raises(RuntimeError, match="ANAM_AVATAR_ID"):
        entrypoint.build_avatar_session(settings)


@pytest.mark.asyncio
async def test_disconnect_cleanup_closes_avatar_and_session() -> None:
    session = Mock(aclose=AsyncMock())
    avatar = Mock(aclose=AsyncMock())
    telemetry = Mock(emit=AsyncMock())

    model_http_session = Mock(close=AsyncMock())

    await entrypoint.close_session_resources(session, avatar, telemetry, model_http_session)

    telemetry.emit.assert_awaited_once_with("session.closed")
    avatar.aclose.assert_awaited_once()
    session.aclose.assert_awaited_once()
    model_http_session.close.assert_awaited_once()
