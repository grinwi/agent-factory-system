"""Provider-agnostic LangChain chat-model construction."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from app.config import Settings


class ModelProviderError(ValueError):
    """Raised when the configured model provider cannot be initialized."""


def _shared_model_kwargs(settings: Settings, *, temperature: float | None) -> dict[str, Any]:
    return {
        "model": settings.llm_model,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "timeout": settings.llm_timeout_seconds,
        "max_retries": 2,
    }


def _build_openai_model(settings: Settings, *, temperature: float | None) -> Any:
    module = import_module("langchain_openai")
    kwargs = _shared_model_kwargs(settings, temperature=temperature)
    base_url = settings.openai_base_url or settings.llm_base_url
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    if base_url:
        kwargs["base_url"] = base_url
    return module.ChatOpenAI(**kwargs)


def _build_anthropic_model(settings: Settings, *, temperature: float | None) -> Any:
    module = import_module("langchain_anthropic")
    kwargs = _shared_model_kwargs(settings, temperature=temperature)
    base_url = settings.anthropic_base_url or settings.llm_base_url
    if settings.anthropic_api_key:
        kwargs["anthropic_api_key"] = settings.anthropic_api_key
    if base_url:
        kwargs["anthropic_api_url"] = base_url
    return module.ChatAnthropic(**kwargs)


def _build_gemini_model(settings: Settings, *, temperature: float | None) -> Any:
    module = import_module("langchain_google_genai")
    kwargs = _shared_model_kwargs(settings, temperature=temperature)
    if settings.google_api_key:
        kwargs["api_key"] = settings.google_api_key
    if settings.google_cloud_project:
        kwargs["project"] = settings.google_cloud_project
    if settings.google_cloud_location:
        kwargs["location"] = settings.google_cloud_location
    if settings.google_use_vertexai is not None:
        kwargs["vertexai"] = settings.google_use_vertexai
    return module.ChatGoogleGenerativeAI(**kwargs)


def build_chat_model(settings: Settings, *, temperature: float | None = None) -> Any:
    """Construct the configured LangChain chat model."""

    provider = settings.llm_provider
    if provider == "openai":
        return _build_openai_model(settings, temperature=temperature)
    if provider == "anthropic":
        return _build_anthropic_model(settings, temperature=temperature)
    if provider == "gemini":
        return _build_gemini_model(settings, temperature=temperature)
    raise ModelProviderError(f"Unsupported LLM provider: {provider}")
