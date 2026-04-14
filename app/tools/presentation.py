"""Dashboard-oriented summaries built from the validated analysis output."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from app.schemas import (
    AnalysisDashboardResponse,
    AnalysisResponse,
    ChartDatum,
    MachineInsight,
    MetricInsight,
    MetricName,
    ThresholdConfig,
)
from app.tools.data_loader import build_plant_snapshot, normalize_dataframe

METRIC_ORDER: tuple[MetricName, ...] = (
    "temperature",
    "error_rate",
    "downtime_minutes",
)

METRIC_META: dict[MetricName, dict[str, str | int]] = {
    "temperature": {
        "label": "Temperature",
        "unit": "C",
        "color": "#C65D2E",
        "precision": 2,
    },
    "error_rate": {
        "label": "Error Rate",
        "unit": "%",
        "color": "#1F6AA5",
        "precision": 4,
    },
    "downtime_minutes": {
        "label": "Downtime",
        "unit": "min",
        "color": "#5C7A2B",
        "precision": 2,
    },
}

SEVERITY_ORDER = ("critical", "high", "medium", "low")
SEVERITY_COLORS = {
    "critical": "#9F1D1D",
    "high": "#D0662D",
    "medium": "#C9A227",
    "low": "#3D7A58",
}


def _round_metric(metric: MetricName, value: float) -> float:
    precision = int(METRIC_META[metric]["precision"])
    return round(float(value), precision)


def _issue_metric(issue: dict[str, Any]) -> MetricName | None:
    raw_metric = issue.get("metric") or issue.get("issue_type")
    if not isinstance(raw_metric, str):
        return None

    normalized = raw_metric.strip().lower()
    if normalized == "downtime":
        normalized = "downtime_minutes"
    if normalized not in METRIC_META:
        return None
    return normalized  # type: ignore[return-value]


def _issue_severity(issue: dict[str, Any]) -> str | None:
    raw_severity = issue.get("severity")
    if not isinstance(raw_severity, str):
        return None

    normalized = raw_severity.strip().lower()
    if normalized in SEVERITY_COLORS:
        return normalized
    return None


def build_metric_cards(
    frame: pd.DataFrame,
    thresholds: ThresholdConfig,
) -> list[MetricInsight]:
    """Build threshold-aware summary cards for each monitored metric."""

    normalized = normalize_dataframe(frame)
    cards: list[MetricInsight] = []

    for metric in METRIC_ORDER:
        threshold = float(getattr(thresholds, metric))
        breached_rows = normalized[normalized[metric] > threshold]
        ratio = float(normalized[metric].max()) / threshold if threshold else 0.0
        status = "stable"
        if len(breached_rows) > 0:
            status = "alert" if ratio >= 1.2 else "watch"

        cards.append(
            MetricInsight(
                metric=metric,
                label=str(METRIC_META[metric]["label"]),
                unit=str(METRIC_META[metric]["unit"]),
                average_value=_round_metric(metric, float(normalized[metric].mean())),
                max_value=_round_metric(metric, float(normalized[metric].max())),
                threshold=_round_metric(metric, threshold),
                breach_count=int(len(breached_rows)),
                impacted_machine_count=int(breached_rows["machine_id"].nunique()),
                status=status,
            )
        )

    return cards


def build_issue_breakdown(analysis_result: AnalysisResponse) -> list[ChartDatum]:
    """Return chart-ready issue counts grouped by metric."""

    counts = Counter()
    for issue in analysis_result.issues:
        metric = _issue_metric(issue)
        if metric is not None:
            counts[metric] += 1

    return [
        ChartDatum(
            label=str(METRIC_META[metric]["label"]),
            value=float(counts.get(metric, 0)),
            color=str(METRIC_META[metric]["color"]),
        )
        for metric in METRIC_ORDER
    ]


def build_severity_breakdown(analysis_result: AnalysisResponse) -> list[ChartDatum]:
    """Return chart-ready issue counts grouped by severity."""

    counts = Counter()
    for issue in analysis_result.issues:
        severity = _issue_severity(issue)
        if severity is not None:
            counts[severity] += 1

    return [
        ChartDatum(
            label=severity.title(),
            value=float(counts.get(severity, 0)),
            color=SEVERITY_COLORS[severity],
        )
        for severity in SEVERITY_ORDER
    ]


def build_machine_breakdown(
    frame: pd.DataFrame,
    analysis_result: AnalysisResponse,
) -> list[MachineInsight]:
    """Return the most affected machines for hotspot-style dashboard views."""

    normalized = normalize_dataframe(frame)
    issue_counts = Counter(
        str(issue.get("machine_id"))
        for issue in analysis_result.issues
        if issue.get("machine_id")
    )

    aggregated = (
        normalized.groupby("machine_id", as_index=False)
        .agg(
            average_temperature=("temperature", "mean"),
            average_error_rate=("error_rate", "mean"),
            total_downtime_minutes=("downtime_minutes", "sum"),
        )
        .assign(
            issue_count=lambda data: data["machine_id"].map(issue_counts).fillna(0).astype(int)
        )
        .sort_values(
            by=[
                "issue_count",
                "total_downtime_minutes",
                "average_temperature",
                "average_error_rate",
            ],
            ascending=[False, False, False, False],
        )
        .head(6)
    )

    return [
        MachineInsight(
            machine_id=str(row.machine_id),
            issue_count=int(row.issue_count),
            average_temperature=round(float(row.average_temperature), 2),
            average_error_rate=round(float(row.average_error_rate), 4),
            total_downtime_minutes=round(float(row.total_downtime_minutes), 2),
        )
        for row in aggregated.itertuples(index=False)
    ]


def build_dashboard_response(
    *,
    analysis_result: AnalysisResponse,
    frame: pd.DataFrame,
    thresholds: ThresholdConfig,
    thread_id: str,
    source_name: str | None = None,
) -> AnalysisDashboardResponse:
    """Build the full human-facing dashboard payload from a validated analysis."""

    normalized = normalize_dataframe(frame)
    return AnalysisDashboardResponse(
        source_name=source_name,
        thread_id=thread_id,
        analysis_result=analysis_result,
        plant_snapshot=build_plant_snapshot(normalized),
        thresholds=thresholds,
        metric_cards=build_metric_cards(normalized, thresholds),
        issue_breakdown=build_issue_breakdown(analysis_result),
        severity_breakdown=build_severity_breakdown(analysis_result),
        machine_breakdown=build_machine_breakdown(normalized, analysis_result),
    )
