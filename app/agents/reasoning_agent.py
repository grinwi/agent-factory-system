"""Reasoning agent for root-cause analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain.tools import ToolRuntime, tool

from app.agents.base import BaseManufacturingAgent
from app.config import Settings
from app.schemas import (
    DetectedIssue,
    PlantSnapshot,
    ReasoningAgentResponse,
)
from app.tools.recommendation_rules import derive_root_cause_hints, issue_pattern_summary


REASONING_PROMPT = """
You are the Reasoning Agent in a manufacturing analytics pipeline.

Responsibilities:
- Analyze the detected issues.
- Infer likely root causes.
- Explain the operational problem clearly and concisely.

Instructions:
- Call the available tools before responding.
- Keep reasoning grounded in the issue evidence and plant snapshot.
- Think step by step privately, but only return the concise structured result.
- Mention uncertainty when evidence is partial.
""".strip()


@dataclass(frozen=True)
class ReasoningAgentContext:
    """Runtime context for the reasoning agent."""

    issues: list[dict[str, Any]]
    issue_summary: str
    plant_snapshot: dict[str, Any]
    thread_id: str


@tool
def summarize_issue_patterns(runtime: ToolRuntime[ReasoningAgentContext]) -> str:
    """Summarize issue counts by metric, severity, and machine for root-cause analysis."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    return json.dumps(issue_pattern_summary(issues), indent=2)


@tool
def fetch_root_cause_hints(runtime: ToolRuntime[ReasoningAgentContext]) -> str:
    """Return deterministic root-cause hints and any previous report for this thread."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    plant_snapshot = PlantSnapshot.model_validate(runtime.context.plant_snapshot)
    hints = derive_root_cause_hints(issues, plant_snapshot)

    previous_report: dict[str, Any] | None = None
    if runtime.store is not None:
        if memory_item := runtime.store.get(("manufacturing_reports",), runtime.context.thread_id):
            previous_report = memory_item.value

    return json.dumps(
        {
            "issue_summary": runtime.context.issue_summary,
            "root_cause_hints": hints,
            "previous_report": previous_report,
        },
        indent=2,
    )


class ReasoningAgent(BaseManufacturingAgent[ReasoningAgentContext, ReasoningAgentResponse]):
    """LangChain agent that explains likely root causes."""

    response_model = ReasoningAgentResponse
    model_temperature = 0.1

    def __init__(self, settings: Settings, store) -> None:
        super().__init__(settings, store)

    def _build_agent(self):
        return self._create_structured_agent(
            tools=[summarize_issue_patterns, fetch_root_cause_hints],
            context_schema=ReasoningAgentContext,
            system_prompt=REASONING_PROMPT,
        )

    def run(
        self,
        *,
        issues: list[dict[str, Any]],
        issue_summary: str,
        plant_snapshot: dict[str, Any],
        thread_id: str,
    ) -> ReasoningAgentResponse:
        context = ReasoningAgentContext(
            issues=issues,
            issue_summary=issue_summary,
            plant_snapshot=plant_snapshot,
            thread_id=thread_id,
        )
        return self._invoke(
            prompt=(
                "Analyze the issue set, use the pattern and hint tools, and return a concise "
                "root-cause explanation with structured hypotheses."
            ),
            context=context,
            thread_id=thread_id,
        )

