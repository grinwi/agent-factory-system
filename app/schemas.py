"""Shared Pydantic schemas for API I/O and agent hand-offs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MetricName = Literal["temperature", "error_rate", "downtime_minutes"]
SeverityLevel = Literal["low", "medium", "high", "critical"]
PriorityLevel = Literal["low", "medium", "high", "immediate"]
DashboardStatus = Literal["stable", "watch", "alert"]


class ThresholdConfig(BaseModel):
    """Thresholds used by rule-based anomaly detection."""

    temperature: float = Field(default=90.0, gt=0)
    error_rate: float = Field(default=0.03, ge=0, le=1)
    downtime_minutes: float = Field(default=40.0, ge=0)


class ProductionRecord(BaseModel):
    """A single production telemetry row."""

    machine_id: str = Field(min_length=1)
    temperature: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    downtime_minutes: float = Field(ge=0)
    line_id: str | None = None
    station_id: str | None = None
    shift: str | None = None
    planned_production_minutes: float | None = Field(default=None, gt=0)
    good_units: int | None = Field(default=None, ge=0)
    reject_units: int | None = Field(default=None, ge=0)
    ideal_cycle_time_seconds: float | None = Field(default=None, gt=0)


class PlantSnapshot(BaseModel):
    """Aggregated operational overview for the current dataset."""

    record_count: int = Field(ge=0)
    machine_count: int = Field(ge=0)
    average_temperature: float = Field(ge=0)
    average_error_rate: float = Field(ge=0)
    total_downtime_minutes: float = Field(ge=0)
    max_temperature: float = Field(ge=0)
    max_error_rate: float = Field(ge=0)
    max_downtime_minutes: float = Field(ge=0)


class DetectedIssue(BaseModel):
    """A normalized production issue detected from telemetry."""

    issue_id: str = Field(min_length=1)
    machine_id: str = Field(min_length=1)
    metric: MetricName
    observed_value: float = Field(ge=0)
    threshold: float = Field(ge=0)
    severity: SeverityLevel
    anomaly_score: float = Field(ge=0, le=1)
    description: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    supporting_metrics: dict[str, float] = Field(default_factory=dict)


class DataAgentResponse(BaseModel):
    """Structured output from the data analysis agent."""

    issues: list[DetectedIssue] = Field(default_factory=list)
    issue_summary: str = Field(min_length=1)
    plant_snapshot: PlantSnapshot


class RootCauseHypothesis(BaseModel):
    """An LLM-generated root cause hypothesis grounded in detected issues."""

    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    related_issue_ids: list[str] = Field(default_factory=list)


class ReasoningAgentResponse(BaseModel):
    """Structured output from the reasoning agent."""

    analysis: str = Field(min_length=1)
    root_causes: list[RootCauseHypothesis] = Field(default_factory=list)


class SolutionRecommendation(BaseModel):
    """Actionable remediation proposal."""

    title: str = Field(min_length=1)
    priority: PriorityLevel
    rationale: str = Field(min_length=1)
    actions: list[str] = Field(default_factory=list)
    expected_impact: str = Field(min_length=1)
    related_issue_ids: list[str] = Field(default_factory=list)


class SolutionAgentResponse(BaseModel):
    """Structured output from the solution agent."""

    solutions: list[SolutionRecommendation] = Field(default_factory=list)


class ValidationAgentResponse(BaseModel):
    """Structured output from the validation agent."""

    issues: list[DetectedIssue] = Field(default_factory=list)
    analysis: str = Field(min_length=1)
    solutions: list[SolutionRecommendation] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)
    validation_notes: list[str] = Field(default_factory=list)


class AnalyzeJsonRequest(BaseModel):
    """JSON request body accepted by the API endpoint."""

    model_config = ConfigDict(extra="forbid")

    records: list[ProductionRecord] | None = None
    data: list[ProductionRecord] | None = None
    csv_text: str | None = None
    thread_id: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> AnalyzeJsonRequest:
        if not self.records and not self.data and not self.csv_text:
            raise ValueError("Provide `records`, `data`, or `csv_text`.")
        return self

    def resolved_records(self) -> list[ProductionRecord]:
        return self.records or self.data or []


class AnalysisJob(BaseModel):
    """Normalized workflow input."""

    records: list[ProductionRecord] = Field(default_factory=list)
    csv_text: str | None = None
    csv_path: str | None = None
    source_name: str | None = None
    thread_id: str | None = None
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)

    @model_validator(mode="after")
    def validate_source(self) -> AnalysisJob:
        if not self.records and not self.csv_text and not self.csv_path:
            raise ValueError("Provide telemetry records, CSV text, or a CSV path.")
        return self

    @classmethod
    def from_json_request(
        cls,
        request: AnalyzeJsonRequest,
        *,
        source_name: str | None = None,
        thresholds: ThresholdConfig | None = None,
    ) -> AnalysisJob:
        return cls(
            records=request.resolved_records(),
            csv_text=request.csv_text,
            source_name=source_name,
            thread_id=request.thread_id,
            thresholds=thresholds or ThresholdConfig(),
        )


class AnalysisResponse(BaseModel):
    """Strict top-level JSON contract returned by the API and workflow."""

    model_config = ConfigDict(extra="forbid")

    issues: list[dict[str, Any]] = Field(default_factory=list)
    analysis: str = Field(min_length=1)
    solutions: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)


class ChartDatum(BaseModel):
    """Generic numeric chart point used by the web dashboard."""

    label: str = Field(min_length=1)
    value: float = Field(ge=0)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class MetricInsight(BaseModel):
    """Threshold-aware summary card for a monitored production metric."""

    metric: MetricName
    label: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    average_value: float = Field(ge=0)
    max_value: float = Field(ge=0)
    threshold: float = Field(ge=0)
    breach_count: int = Field(ge=0)
    impacted_machine_count: int = Field(ge=0)
    status: DashboardStatus


class MachineInsight(BaseModel):
    """Machine-level summary used for dashboard hotspot views."""

    machine_id: str = Field(min_length=1)
    issue_count: int = Field(ge=0)
    average_temperature: float = Field(ge=0)
    average_error_rate: float = Field(ge=0, le=1)
    total_downtime_minutes: float = Field(ge=0)


class OeeInsight(BaseModel):
    """Overall equipment effectiveness metrics for a production scope."""

    availability: float = Field(ge=0, le=1)
    performance: float = Field(ge=0, le=1)
    quality: float = Field(ge=0, le=1)
    oee: float = Field(ge=0, le=1)
    planned_production_minutes: float = Field(ge=0)
    operating_minutes: float = Field(ge=0)
    downtime_minutes: float = Field(ge=0)
    total_units: int = Field(ge=0)
    good_units: int = Field(ge=0)
    reject_units: int = Field(ge=0)
    status: DashboardStatus


class OeeLineInsight(OeeInsight):
    """Line-level OEE breakdown used by the dashboard and PDF reports."""

    line_id: str = Field(min_length=1)
    machine_count: int = Field(ge=0)


class OeeSummary(BaseModel):
    """Optional OEE summary when a dataset includes throughput fields."""

    available: bool
    source_rows: int = Field(ge=0)
    coverage_rows: int = Field(ge=0)
    benchmark: float = Field(default=0.85, ge=0, le=1)
    narrative: str = Field(min_length=1)
    overall: OeeInsight | None = None
    line_breakdown: list[OeeLineInsight] = Field(default_factory=list)


class AnalysisDashboardResponse(BaseModel):
    """Human-facing analysis payload with chart-ready summaries."""

    model_config = ConfigDict(extra="forbid")

    source_name: str | None = None
    thread_id: str = Field(min_length=1)
    analysis_result: AnalysisResponse
    plant_snapshot: PlantSnapshot
    thresholds: ThresholdConfig
    metric_cards: list[MetricInsight] = Field(default_factory=list)
    issue_breakdown: list[ChartDatum] = Field(default_factory=list)
    severity_breakdown: list[ChartDatum] = Field(default_factory=list)
    machine_breakdown: list[MachineInsight] = Field(default_factory=list)
    oee_summary: OeeSummary | None = None
