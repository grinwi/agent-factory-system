"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from app.schemas import ThresholdConfig

LLMProvider = Literal["openai", "anthropic", "gemini"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


PROVIDER_ALIASES: dict[str, LLMProvider] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
    "google-genai": "gemini",
}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _bool_env(name: str) -> bool | None:
    value = os.getenv(name)
    if value in {None, ""}:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Environment variable {name} must be a boolean string.")


def _first_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in {None, ""}:
            return value
    return default


def normalize_llm_provider(raw_provider: str | None) -> LLMProvider:
    normalized = (raw_provider or "openai").strip().lower()
    if normalized not in PROVIDER_ALIASES:
        supported = ", ".join(sorted(PROVIDER_ALIASES))
        raise ValueError(
            f"Unsupported LLM provider '{raw_provider}'. Supported values: {supported}."
        )
    return PROVIDER_ALIASES[normalized]


def _default_model_for_provider(provider: LLMProvider) -> str:
    defaults: dict[LLMProvider, str] = {
        "openai": "gpt-4.1-mini",
        "anthropic": "claude-haiku-4-5-20251001",
        "gemini": "gemini-2.5-flash",
    }
    return defaults[provider]


def _provider_from_env() -> LLMProvider:
    return normalize_llm_provider(os.getenv("LLM_PROVIDER"))


def _model_from_env() -> str:
    provider = _provider_from_env()
    if provider == "openai":
        model = _first_env("LLM_MODEL", "OPENAI_MODEL")
        return model or _default_model_for_provider(provider)
    if provider == "anthropic":
        model = _first_env("LLM_MODEL", "ANTHROPIC_MODEL")
        return model or _default_model_for_provider(provider)
    model = _first_env(
        "LLM_MODEL",
        "GEMINI_MODEL",
        "GOOGLE_MODEL",
    )
    return model or _default_model_for_provider(provider)


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
    llm_provider: LLMProvider = field(default_factory=_provider_from_env)
    llm_model: str = field(default_factory=_model_from_env)
    llm_temperature: float = field(
        default_factory=lambda: _float_env(
            "LLM_TEMPERATURE",
            _float_env("OPENAI_TEMPERATURE", 0.1),
        )
    )
    llm_timeout_seconds: float = field(
        default_factory=lambda: _float_env(
            "LLM_TIMEOUT_SECONDS",
            _float_env("OPENAI_TIMEOUT_SECONDS", 60.0),
        )
    )
    llm_base_url: str | None = field(default_factory=lambda: _first_env("LLM_BASE_URL"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_base_url: str | None = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_base_url: str | None = field(
        default_factory=lambda: _first_env("ANTHROPIC_API_URL", "ANTHROPIC_BASE_URL")
    )
    google_api_key: str | None = field(
        default_factory=lambda: _first_env("GOOGLE_API_KEY", "GEMINI_API_KEY")
    )
    google_cloud_project: str | None = field(
        default_factory=lambda: _first_env("GOOGLE_CLOUD_PROJECT")
    )
    google_cloud_location: str | None = field(
        default_factory=lambda: _first_env("GOOGLE_CLOUD_LOCATION")
    )
    google_use_vertexai: bool | None = field(
        default_factory=lambda: _bool_env("GOOGLE_GENAI_USE_VERTEXAI")
    )
    thresholds: ThresholdConfig = field(default_factory=_thresholds_from_env)

    def __post_init__(self) -> None:
        object.__setattr__(self, "llm_provider", normalize_llm_provider(self.llm_provider))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
