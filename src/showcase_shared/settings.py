from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_AGENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    livekit_url: str = "ws://localhost:7880"
    public_livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"
    agent_name: str = "showcase-voice-agent"

    openai_api_key: str = ""
    openai_realtime_model: str = "gpt-realtime-2.1"

    anam_api_key: str = ""
    anam_avatar_id: str = ""
    showcase_avatar_enabled: bool = False

    business_api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./data/showcase.db"
    log_level: str = "INFO"
    showcase_access_code: str = ""

    tool_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    model_connect_timeout_seconds: float = Field(default=20.0, ge=5, le=60)
    agent_health_port: int = Field(default=8081, ge=1024, le=65535)
    openai_http_proxy: str = ""

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, value: str) -> str:
        value = value.strip()
        if not _AGENT_NAME.fullmatch(value):
            raise ValueError("AGENT_NAME contains unsupported characters")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
        return normalized

    @field_validator("openai_http_proxy")
    @classmethod
    def validate_openai_http_proxy(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return ""
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OPENAI_HTTP_PROXY must be an HTTP(S) URL")
        return normalized

    def require_live_agent_credentials(self) -> None:
        missing = [
            name
            for name, value in (
                ("OPENAI_API_KEY", self.openai_api_key),
                ("LIVEKIT_API_KEY", self.livekit_api_key),
                ("LIVEKIT_API_SECRET", self.livekit_api_secret),
            )
            if not value.strip()
        ]
        if self.showcase_avatar_enabled:
            missing.extend(
                name
                for name, value in (
                    ("ANAM_API_KEY", self.anam_api_key),
                    ("ANAM_AVATAR_ID", self.anam_avatar_id),
                )
                if not value.strip()
            )
        if missing:
            raise RuntimeError(f"Missing required runtime variables: {', '.join(missing)}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
