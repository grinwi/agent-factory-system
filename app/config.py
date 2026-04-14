"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from app.schemas import ThresholdConfig


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _thresholds_from_env() -> ThresholdConfig:
    return ThresholdConfig(
        temperature=_float_env("TEMP_THRESHOLD", 90.0),
        error_rate=_float_env("ERROR_RATE_THRESHOLD", 0.03),
        downtime_minutes=_float_env("DOWNTIME_THRESHOLD", 40.0),
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the multi-agent service."""

    app_name: str = "Manufacturing Analytics Multi-Agent Assistant"
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_base_url: str | None = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    openai_temperature: float = field(
        default_factory=lambda: _float_env("OPENAI_TEMPERATURE", 0.1)
    )
    openai_timeout_seconds: float = field(
        default_factory=lambda: _float_env("OPENAI_TIMEOUT_SECONDS", 60.0)
    )
    thresholds: ThresholdConfig = field(default_factory=_thresholds_from_env)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()

