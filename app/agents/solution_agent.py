"""Solution agent that proposes prioritized remediations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain.tools import ToolRuntime, tool

from app.agents.base import BaseManufacturingAgent
from app.config import Settings
from app.schemas import DetectedIssue, RootCauseHypothesis, SolutionAgentResponse
from app.tools.recommendation_rules import build_solution_playbook, prioritization_rules

SOLUTION_PROMPT = """
You are the Solution Agent in a manufacturing analytics workflow.

Responsibilities:
- Suggest actionable fixes for the detected issues.
- Prioritize recommendations by urgency and impact.
- Keep recommendations specific, operational, and implementation-ready.

Instructions:
- Use the available tools before responding.
- Tie each recommendation back to relevant issue IDs.
- Prefer a short set of high-signal recommendations over a long generic list.
- Do not invent unsupported equipment details.
""".strip()


@dataclass(frozen=True)
class SolutionAgentContext:
    """Runtime context for the solution agent."""

    issues: list[dict[str, Any]]
    root_causes: list[dict[str, Any]]
    analysis: str
    plant_snapshot: dict[str, Any]
    thread_id: str


@tool
def build_rule_based_playbook(runtime: ToolRuntime[SolutionAgentContext]) -> str:
    """Generate deterministic remediation actions grounded in the issue set."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    return json.dumps(build_solution_playbook(issues), indent=2)


@tool
def fetch_priority_rules(runtime: ToolRuntime[SolutionAgentContext]) -> str:
    """Return prioritization rules, root causes, and any prior report for this thread."""

    issues = [DetectedIssue.model_validate(item) for item in runtime.context.issues]
    root_causes = [
        RootCauseHypothesis.model_validate(item) for item in runtime.context.root_causes
    ]

    previous_report: dict[str, Any] | None = None
    if runtime.store is not None:
        if memory_item := runtime.store.get(("manufacturing_reports",), runtime.context.thread_id):
            previous_report = memory_item.value

    return json.dumps(
        {
            "priority_rules": prioritization_rules(issues),
            "analysis": runtime.context.analysis,
            "root_causes": [root_cause.model_dump(mode="json") for root_cause in root_causes],
            "previous_report": previous_report,
        },
        indent=2,
    )


class SolutionAgent(BaseManufacturingAgent[SolutionAgentContext, SolutionAgentResponse]):
    """LangChain agent that turns issues into actionable recommendations."""

    response_model = SolutionAgentResponse
    model_temperature = 0.15

    def __init__(self, settings: Settings, store) -> None:
        super().__init__(settings, store)

    def _build_agent(self):
        return self._create_structured_agent(
            tools=[build_rule_based_playbook, fetch_priority_rules],
            context_schema=SolutionAgentContext,
            system_prompt=SOLUTION_PROMPT,
        )

    def run(
        self,
        *,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
        analysis: str,
        plant_snapshot: dict[str, Any],
        thread_id: str,
    ) -> SolutionAgentResponse:
        context = SolutionAgentContext(
            issues=issues,
            root_causes=root_causes,
            analysis=analysis,
            plant_snapshot=plant_snapshot,
            thread_id=thread_id,
        )
        return self._invoke(
            prompt=(
                "Use the solution playbook and priority tools to produce a structured list "
                "of actionable recommendations."
            ),
            context=context,
            thread_id=thread_id,
        )

