from __future__ import annotations

from pathlib import Path

import pytest

from app.bootstrap_support import (
    build_env_values,
    normalize_provider_choice,
    parse_env_file,
    render_env_file,
    validate_runtime_env,
)


@pytest.mark.parametrize(
    ("raw_provider", "expected"),
    [
        ("openai", "openai"),
        ("claude", "anthropic"),
        ("anthropic", "anthropic"),
        ("google", "gemini"),
        ("gemini", "gemini"),
    ],
)
def test_normalize_provider_choice_handles_aliases(
    raw_provider: str,
    expected: str,
) -> None:
    assert normalize_provider_choice(raw_provider) == expected


def test_parse_env_file_ignores_comments_and_strips_quotes(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Comment line\n"
        "LLM_PROVIDER=openai\n"
        "OPENAI_API_KEY='test-key'\n"
        "EXTRA_VALUE=\"demo\"\n",
        encoding="utf-8",
    )

    parsed = parse_env_file(env_path)

    assert parsed == {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-key",
        "EXTRA_VALUE": "demo",
    }


def test_build_env_values_updates_selected_provider_and_preserves_other_values() -> None:
    env_values = build_env_values(
        selected_provider="claude",
        api_key="anthropic-secret",
        existing_env={
            "OPENAI_API_KEY": "existing-openai-key",
            "TEMP_THRESHOLD": "95",
        },
        model="claude-3-5-haiku-latest",
        base_url="https://anthropic.example.test",
    )

    assert env_values["LLM_PROVIDER"] == "anthropic"
    assert env_values["LLM_MODEL"] == "claude-3-5-haiku-latest"
    assert env_values["ANTHROPIC_API_KEY"] == "anthropic-secret"
    assert env_values["ANTHROPIC_MODEL"] == "claude-3-5-haiku-latest"
    assert env_values["ANTHROPIC_API_URL"] == "https://anthropic.example.test"
    assert env_values["OPENAI_API_KEY"] == "existing-openai-key"
    assert env_values["TEMP_THRESHOLD"] == "95"


def test_render_env_file_preserves_additional_overrides() -> None:
    rendered = render_env_file(
        {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4.1-mini",
            "OPENAI_API_KEY": "openai-secret",
            "CUSTOM_FLAG": "enabled",
        }
    )

    assert "# Local configuration for Manufacturing Analytics Multi-Agent System" in rendered
    assert "OPENAI_API_KEY=openai-secret" in rendered
    assert "# Additional local overrides" in rendered
    assert "CUSTOM_FLAG=enabled" in rendered


def test_validate_runtime_env_requires_real_api_key() -> None:
    problems = validate_runtime_env(
        {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4.1-mini",
            "OPENAI_API_KEY": "your-api-key",
        }
    )

    assert problems == ["Missing a real API key for OpenAI (OPENAI_API_KEY)."]


def test_validate_runtime_env_accepts_complete_configuration() -> None:
    problems = validate_runtime_env(
        {
            "LLM_PROVIDER": "gemini",
            "LLM_MODEL": "gemini-2.5-flash",
            "GOOGLE_API_KEY": "gemini-secret",
        }
    )

    assert problems == []
