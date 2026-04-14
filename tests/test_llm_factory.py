from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import Settings, _bool_env, normalize_llm_provider
from app.llm_factory import build_chat_model


@pytest.mark.parametrize(
    ("raw_provider", "expected"),
    [
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("claude", "anthropic"),
        ("gemini", "gemini"),
        ("google", "gemini"),
    ],
)
def test_normalize_llm_provider_aliases(raw_provider: str, expected: str) -> None:
    assert normalize_llm_provider(raw_provider) == expected


def test_blank_optional_boolean_env_is_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "")

    assert _bool_env("GOOGLE_GENAI_USE_VERTEXAI") is None

    settings = Settings(
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        google_api_key="google-test-key",
    )
    assert settings.google_use_vertexai is None


@pytest.mark.parametrize(
    ("provider", "module_name", "class_name", "expected_model"),
    [
        ("openai", "langchain_openai", "ChatOpenAI", "gpt-4.1-mini"),
        ("anthropic", "langchain_anthropic", "ChatAnthropic", "claude-haiku-test"),
        ("gemini", "langchain_google_genai", "ChatGoogleGenerativeAI", "gemini-2.5-flash"),
    ],
)
def test_build_chat_model_selects_provider_client(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    module_name: str,
    class_name: str,
    expected_model: str,
) -> None:
    created: dict[str, object] = {}

    class FakeChatModel:
        def __init__(self, **kwargs):
            created.update(kwargs)

    def fake_import(name: str):
        assert name == module_name
        return SimpleNamespace(**{class_name: FakeChatModel})

    monkeypatch.setattr("app.llm_factory.import_module", fake_import)

    settings = Settings(
        llm_provider=provider,
        llm_model=expected_model,
        llm_temperature=0.25,
        llm_timeout_seconds=19.0,
        openai_api_key="openai-test-key",
        anthropic_api_key="anthropic-test-key",
        google_api_key="google-test-key",
        anthropic_base_url="https://anthropic.example.test",
        google_cloud_project="demo-project",
        google_cloud_location="us-central1",
        google_use_vertexai=True,
    )

    model = build_chat_model(settings, temperature=0.05)

    assert isinstance(model, FakeChatModel)
    assert created["model"] == expected_model
    assert created["temperature"] == 0.05
    assert created["timeout"] == 19.0
    assert created["max_retries"] == 2

    if provider == "openai":
        assert created["api_key"] == "openai-test-key"
    elif provider == "anthropic":
        assert created["anthropic_api_key"] == "anthropic-test-key"
        assert created["anthropic_api_url"] == "https://anthropic.example.test"
    else:
        assert created["api_key"] == "google-test-key"
        assert created["project"] == "demo-project"
        assert created["location"] == "us-central1"
        assert created["vertexai"] is True
