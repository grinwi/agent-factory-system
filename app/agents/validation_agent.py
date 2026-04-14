"""Validation agent that checks consistency and final JSON readiness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain.tools import ToolRuntime, tool

from app.agents.base import BaseManufacturingAgent
from app.config import Settings
from app.schemas import (
    DetectedIssue,
    RootCauseHypothesis,
    SolutionRecommendation,
    ValidationAgentResponse,
)
from app.tools.validation import (
    guard_against_hallucinations,
    run_consistency_checks,
    suggest_confidence_score,
)

VALIDATION_PROMPT = """
You are the Validation Agent in a manufacturing analytics pipeline.

Responsibilities:
- Validate output consistency.
- Ensure the final response stays grounded in the detected issues.
- Produce a strict JSON-ready result with a confidence score from 0.0 to 1.0.

Instructions:
- Use every available validation tool before responding.
- Preserve the original issue list unless a correction is clearly required.
- Keep the analysis concise and factual.
- If you detect inconsistency, repair it directly in the structured output.
""".strip()


@dataclass(frozen=True)
class ValidationAgentContext:
    """Runtime context for the validation agent."""

    issues: list[dict[str, Any]]
    analysis: str
    root_causes: list[dict[str, Any]]
    solutions: list[dict[str, Any]]
    issue_summary: str
    plant_snapshot: dict[str, Any]
    thread_id: str


@tool
def run_consistency_validation(runtime: ToolRuntime[ValidationAgentContext]) -> str:
    """Run deterministic checks over issues, analysis, and recommendations."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    root_causes = [
        RootCauseHypothesis.model_validate(item) for item in runtime.context.root_causes
    ]
    solutions = [
        SolutionRecommendation.model_validate(item) for item in runtime.context.solutions
    ]

    findings = run_consistency_checks(
        issues=issues,
        analysis=runtime.context.analysis,
        root_causes=root_causes,
        solutions=solutions,
    )
    confidence = suggest_confidence_score(
        issues=issues,
        findings=findings,
        solutions=solutions,
        root_causes=root_causes,
    )
    return json.dumps(
        {
            "issue_summary": runtime.context.issue_summary,
            "consistency_findings": findings,
            "suggested_confidence_score": confidence,
        },
        indent=2,
    )


@tool
def run_hallucination_guard(runtime: ToolRuntime[ValidationAgentContext]) -> str:
    """Check for unsupported claims or machine references in the output."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    root_causes = [
        RootCauseHypothesis.model_validate(item) for item in runtime.context.root_causes
    ]
    solutions = [
        SolutionRecommendation.model_validate(item) for item in runtime.context.solutions
    ]

    previous_report: dict[str, Any] | None = None
    if runtime.store is not None:
        if memory_item := runtime.store.get(("manufacturing_reports",), runtime.context.thread_id):
            previous_report = memory_item.value

    payload = guard_against_hallucinations(
        issues=issues,
        analysis=runtime.context.analysis,
        root_causes=root_causes,
        solutions=solutions,
    )
    payload["previous_report"] = previous_report
    payload["plant_snapshot"] = runtime.context.plant_snapshot
    return json.dumps(payload, indent=2)


class ValidationAgent(
    BaseManufacturingAgent[ValidationAgentContext, ValidationAgentResponse]
):
    """LangChain agent that validates and finalizes the JSON response."""

    response_model = ValidationAgentResponse
    model_temperature = 0.0

    def __init__(self, settings: Settings, store) -> None:
        super().__init__(settings, store)

    def _build_agent(self):
        return self._create_structured_agent(
            tools=[run_consistency_validation, run_hallucination_guard],
            context_schema=ValidationAgentContext,
            system_prompt=VALIDATION_PROMPT,
        )

    def run(
        self,
        *,
        issues: list[dict[str, Any]],
        analysis: str,
        root_causes: list[dict[str, Any]],
        solutions: list[dict[str, Any]],
        issue_summary: str,
        plant_snapshot: dict[str, Any],
        thread_id: str,
    ) -> ValidationAgentResponse:
        context = ValidationAgentContext(
            issues=issues,
            analysis=analysis,
            root_causes=root_causes,
            solutions=solutions,
            issue_summary=issue_summary,
            plant_snapshot=plant_snapshot,
            thread_id=thread_id,
        )
        return self._invoke(
            prompt=(
                "Validate the assembled manufacturing report with the consistency and "
                "hallucination tools, then return the corrected final output."
            ),
            context=context,
            thread_id=thread_id,
        )

