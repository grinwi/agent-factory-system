"""Shared base utilities for the manufacturing LangChain agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel

from app.config import Settings


ResponseT = TypeVar("ResponseT", bound=BaseModel)
ContextT = TypeVar("ContextT")


class BaseManufacturingAgent(ABC, Generic[ContextT, ResponseT]):
    """Base class for the production analytics agents."""

    response_model: type[ResponseT]
    model_temperature: float = 0.1

    def __init__(self, settings: Settings, store: InMemoryStore) -> None:
        self.settings = settings
        self.store = store
        self._agent: Runnable | None = None

    def _build_model(self) -> ChatOpenAI:
        model_kwargs: dict[str, object] = {
            "model": self.settings.openai_model,
            "temperature": self.model_temperature,
            "timeout": self.settings.openai_timeout_seconds,
            "max_retries": 2,
        }
        if self.settings.openai_api_key:
            model_kwargs["api_key"] = self.settings.openai_api_key
        if self.settings.openai_base_url:
            model_kwargs["base_url"] = self.settings.openai_base_url
        return ChatOpenAI(**model_kwargs)

    @abstractmethod
    def _build_agent(self) -> Runnable:
        """Build the underlying LangChain agent."""

    def _get_agent(self) -> Runnable:
        if self._agent is None:
            self._agent = self._build_agent()
        return self._agent

    def _invoke(self, *, prompt: str, context: ContextT, thread_id: str) -> ResponseT:
        result = self._get_agent().invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            context=context,
            config={"configurable": {"thread_id": thread_id}},
        )
        structured_response = result["structured_response"]
        if isinstance(structured_response, self.response_model):
            return structured_response
        return self.response_model.model_validate(structured_response)

    def _create_structured_agent(
        self,
        *,
        tools: list[object],
        context_schema: type[ContextT],
        system_prompt: str,
    ) -> Runnable:
        return create_agent(
            self._build_model(),
            tools=tools,
            context_schema=context_schema,
            response_format=ToolStrategy(self.response_model),
            store=self.store,
            system_prompt=system_prompt,
        )

