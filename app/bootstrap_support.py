"""Helpers for local BYOK bootstrap and launch flows."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProviderBootstrapConfig:
    """Configuration metadata used by the local setup wizard."""

    slug: str
    label: str
    api_key_env: str
    model_env: str
    default_model: str
    base_url_env: str | None = None


PROVIDER_ALIASES: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
    "google-genai": "gemini",
}

PROVIDER_CONFIGS: dict[str, ProviderBootstrapConfig] = {
    "openai": ProviderBootstrapConfig(
        slug="openai",
        label="OpenAI",
        api_key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
        default_model="gpt-4.1-mini",
        base_url_env="OPENAI_BASE_URL",
    ),
    "anthropic": ProviderBootstrapConfig(
        slug="anthropic",
        label="Anthropic Claude",
        api_key_env="ANTHROPIC_API_KEY",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-haiku-4-5-20251001",
        base_url_env="ANTHROPIC_API_URL",
    ),
    "gemini": ProviderBootstrapConfig(
        slug="gemini",
        label="Google Gemini",
        api_key_env="GOOGLE_API_KEY",
        model_env="GEMINI_MODEL",
        default_model="gemini-2.5-flash",
    ),
}

DEFAULT_ENV_VALUES: dict[str, str] = {
    "LLM_PROVIDER": "openai",
    "LLM_MODEL": "gpt-4.1-mini",
    "LLM_TEMPERATURE": "0.1",
    "LLM_TIMEOUT_SECONDS": "60",
    "LLM_BASE_URL": "",
    "OPENAI_API_KEY": "",
    "OPENAI_BASE_URL": "",
    "OPENAI_MODEL": "gpt-4.1-mini",
    "OPENAI_TEMPERATURE": "0.1",
    "OPENAI_TIMEOUT_SECONDS": "60",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_API_URL": "",
    "ANTHROPIC_MODEL": "claude-haiku-4-5-20251001",
    "GOOGLE_API_KEY": "",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "GOOGLE_GENAI_USE_VERTEXAI": "",
    "GOOGLE_CLOUD_PROJECT": "",
    "GOOGLE_CLOUD_LOCATION": "",
    "TEMP_THRESHOLD": "90",
    "ERROR_RATE_THRESHOLD": "0.03",
    "DOWNTIME_THRESHOLD": "40",
}

ENV_FILE_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Core model runtime",
        [
            "LLM_PROVIDER",
            "LLM_MODEL",
            "LLM_TEMPERATURE",
            "LLM_TIMEOUT_SECONDS",
            "LLM_BASE_URL",
        ],
    ),
    (
        "OpenAI",
        [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_MODEL",
            "OPENAI_TEMPERATURE",
            "OPENAI_TIMEOUT_SECONDS",
        ],
    ),
    (
        "Anthropic Claude",
        [
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_API_URL",
            "ANTHROPIC_MODEL",
        ],
    ),
    (
        "Google Gemini",
        [
            "GOOGLE_API_KEY",
            "GEMINI_MODEL",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
        ],
    ),
    (
        "Detection thresholds",
        [
            "TEMP_THRESHOLD",
            "ERROR_RATE_THRESHOLD",
            "DOWNTIME_THRESHOLD",
        ],
    ),
]

PLACEHOLDER_API_KEYS = {
    "",
    "your-api-key",
    "paste-your-api-key-here",
    "changeme",
}


def normalize_provider_choice(raw_provider: str | None) -> str:
    """Normalize provider aliases used by the setup helpers."""

    normalized = (raw_provider or "openai").strip().lower()
    if normalized not in PROVIDER_ALIASES:
        supported = ", ".join(sorted(PROVIDER_ALIASES))
        raise ValueError(
            f"Unsupported provider '{raw_provider}'. Supported values: {supported}."
        )
    return PROVIDER_ALIASES[normalized]


def get_provider_config(raw_provider: str | None) -> ProviderBootstrapConfig:
    """Return the bootstrap configuration for the selected provider."""

    return PROVIDER_CONFIGS[normalize_provider_choice(raw_provider)]


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a minimal `.env` file into a dictionary."""

    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", maxsplit=1)
        values[key.strip()] = _strip_matching_quotes(value.strip())
    return values


def build_env_values(
    *,
    selected_provider: str,
    api_key: str,
    existing_env: Mapping[str, str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    """Build a complete `.env` mapping for the local setup flow."""

    provider_config = get_provider_config(selected_provider)
    env_values = dict(DEFAULT_ENV_VALUES)
    env_values.update(existing_env or {})

    resolved_model = (
        (model or "").strip()
        or env_values.get(provider_config.model_env, "").strip()
        or provider_config.default_model
    )

    env_values["LLM_PROVIDER"] = provider_config.slug
    env_values["LLM_MODEL"] = resolved_model
    env_values[provider_config.api_key_env] = api_key.strip()
    env_values[provider_config.model_env] = resolved_model

    if provider_config.base_url_env and base_url is not None:
        env_values[provider_config.base_url_env] = base_url.strip()

    for key, default in DEFAULT_ENV_VALUES.items():
        env_values.setdefault(key, default)

    return env_values


def render_env_file(env_values: Mapping[str, str]) -> str:
    """Render the `.env` file in a stable, human-readable order."""

    lines = [
        "# Local configuration for Manufacturing Analytics Multi-Agent System",
        "# Keep this file on your machine. It is ignored by git.",
        "",
    ]

    known_keys: set[str] = set()
    for section_title, keys in ENV_FILE_SECTIONS:
        lines.append(f"# {section_title}")
        for key in keys:
            lines.append(f"{key}={env_values.get(key, DEFAULT_ENV_VALUES.get(key, ''))}")
            known_keys.add(key)
        lines.append("")

    extra_keys = sorted(key for key in env_values if key not in known_keys)
    if extra_keys:
        lines.append("# Additional local overrides")
        for key in extra_keys:
            lines.append(f"{key}={env_values[key]}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def validate_runtime_env(env_values: Mapping[str, str]) -> list[str]:
    """Validate that the local runtime has enough configuration to start safely."""

    provider_config = get_provider_config(env_values.get("LLM_PROVIDER"))
    api_key = env_values.get(provider_config.api_key_env, "").strip()
    model = (
        env_values.get("LLM_MODEL", "").strip()
        or env_values.get(provider_config.model_env, "").strip()
    )
    problems: list[str] = []

    if api_key.lower() in PLACEHOLDER_API_KEYS:
        problems.append(
            f"Missing a real API key for {provider_config.label} "
            f"({provider_config.api_key_env})."
        )
    if not model:
        problems.append(
            f"Missing a model name for {provider_config.label} ({provider_config.model_env})."
        )

    return problems


def venv_python_path(project_root: Path) -> Path:
    """Return the expected Python executable path inside `.venv`."""

    if os.name == "nt":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def _strip_matching_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
