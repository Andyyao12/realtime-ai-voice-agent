from __future__ import annotations

from pathlib import Path

import pytest

from showcase_shared.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'showcase.db'}",
        showcase_avatar_enabled=False,
        openai_api_key="test-openai-key",
        livekit_api_key="test-livekit-key",
        livekit_api_secret="test-livekit-secret",
    )
