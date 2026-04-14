"""Data analysis agent for production telemetry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain.tools import ToolRuntime, tool

from app.agents.base import BaseManufacturingAgent
from app.config import Settings
from app.schemas import DataAgentResponse, ThresholdConfig
from app.tools.anomaly_detection import detect_anomaly_models, summarize_issues
from app.tools.data_loader import build_plant_snapshot, load_production_data

DATA_ANALYSIS_PROMPT = """
You are the Data Analysis Agent for a manufacturing analytics system.

Responsibilities:
- Load the current production dataset with pandas.
- Detect anomalies using the rule-based detector.
- Summarize the issues in a grounded, production-oriented way.

Instructions:
- Always call both tools before answering.
- Use only the evidence returned by the tools.
- Do not invent machines, metrics, thresholds, or issue counts.
- If no anomalies are detected, return an empty issues list and explain that the line is stable.
""".strip()


@dataclass(frozen=True)
class DataAgentContext:
    """Runtime context injected into the data analysis agent tools."""

    records: list[dict[str, Any]]
    csv_text: str | None
    csv_path: str | None
    thresholds: ThresholdConfig
    thread_id: str
    source_name: str | None = None


@tool
def load_dataset_profile(runtime: ToolRuntime[DataAgentContext]) -> str:
    """Load the current production dataset and summarize plant-level operating metrics."""

    frame = load_production_data(
        records=runtime.context.records,
        csv_text=runtime.context.csv_text,
        csv_path=runtime.context.csv_path,
    )
    snapshot = build_plant_snapshot(frame)
    return snapshot.model_dump_json(indent=2)


@tool
def detect_rule_based_anomalies(runtime: ToolRuntime[DataAgentContext]) -> str:
    """Detect anomalies in temperature, error rate, and downtime using deterministic rules."""

    frame = load_production_data(
        records=runtime.context.records,
        csv_text=runtime.context.csv_text,
        csv_path=runtime.context.csv_path,
    )
    issues = detect_anomaly_models(frame, thresholds=runtime.context.thresholds)
    payload = {
        "issue_count": len(issues),
        "issue_summary": summarize_issues(issues),
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }
    return json.dumps(payload, indent=2)


class DataAnalysisAgent(BaseManufacturingAgent[DataAgentContext, DataAgentResponse]):
    """LangChain agent that handles data loading and anomaly discovery."""

    response_model = DataAgentResponse
    model_temperature = 0.0

    def __init__(self, settings: Settings, store) -> None:
        super().__init__(settings, store)

    def _build_agent(self):
        return self._create_structured_agent(
            tools=[load_dataset_profile, detect_rule_based_anomalies],
            context_schema=DataAgentContext,
            system_prompt=DATA_ANALYSIS_PROMPT,
        )

    def run(
        self,
        *,
        records: list[dict[str, Any]],
        csv_text: str | None,
        csv_path: str | None,
        thresholds: ThresholdConfig,
        thread_id: str,
        source_name: str | None = None,
    ) -> DataAgentResponse:
        context = DataAgentContext(
            records=records,
            csv_text=csv_text,
            csv_path=csv_path,
            thresholds=thresholds,
            thread_id=thread_id,
            source_name=source_name,
        )
        return self._invoke(
            prompt=(
                "Inspect the current telemetry batch, call the dataset profile and anomaly tools, "
                "then return a structured issue summary."
            ),
            context=context,
            thread_id=thread_id,
        )

