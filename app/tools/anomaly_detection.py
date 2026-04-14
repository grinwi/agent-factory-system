"""Rule-based anomaly detection for manufacturing telemetry."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.config import get_settings
from app.schemas import DetectedIssue, SeverityLevel, ThresholdConfig
from app.tools.data_loader import load_production_data, normalize_dataframe

SEVERITY_RANK: dict[SeverityLevel, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _severity_from_ratio(ratio: float) -> SeverityLevel:
    if ratio >= 1.4:
        return "critical"
    if ratio >= 1.2:
        return "high"
    if ratio >= 1.05:
        return "medium"
    return "low"


def _score_from_ratio(ratio: float) -> float:
    score = 0.35 + max(ratio - 1.0, 0.0) * 0.6
    return round(min(score, 1.0), 2)


def _issue_description(machine_id: str, metric: str) -> str:
    if metric == "temperature":
        return f"Machine {machine_id} is operating above the safe temperature envelope."
    if metric == "error_rate":
        return f"Machine {machine_id} error rate suggests process drift or quality instability."
    return f"Machine {machine_id} downtime indicates degraded availability or maintenance backlog."


def detect_anomaly_models(
    frame: pd.DataFrame,
    *,
    thresholds: ThresholdConfig | None = None,
) -> list[DetectedIssue]:
    """Detect threshold breaches and return strongly typed issue models."""

    effective_thresholds = thresholds or get_settings().thresholds
    normalized = normalize_dataframe(frame)
    issues: list[DetectedIssue] = []

    for row_index, row in normalized.reset_index(drop=True).iterrows():
        row_metrics = {
            "temperature": float(row["temperature"]),
            "error_rate": float(row["error_rate"]),
            "downtime_minutes": float(row["downtime_minutes"]),
        }
        machine_id = str(row["machine_id"])

        for metric, observed_value in row_metrics.items():
            threshold_value = float(getattr(effective_thresholds, metric))
            if observed_value <= threshold_value:
                continue

            ratio = observed_value / threshold_value if threshold_value else 1.0
            severity = _severity_from_ratio(ratio)
            issue = DetectedIssue(
                issue_id=f"{machine_id}:{metric}:{row_index}",
                machine_id=machine_id,
                metric=metric,  # type: ignore[arg-type]
                observed_value=round(observed_value, 4),
                threshold=round(threshold_value, 4),
                severity=severity,
                anomaly_score=_score_from_ratio(ratio),
                description=_issue_description(machine_id, metric),
                evidence=(
                    f"{metric} measured at {observed_value:.4f}, exceeding the rule threshold "
                    f"of {threshold_value:.4f}."
                ),
                supporting_metrics={key: round(value, 4) for key, value in row_metrics.items()},
            )
            issues.append(issue)

    issues.sort(
        key=lambda issue: (SEVERITY_RANK[issue.severity], issue.anomaly_score),
        reverse=True,
    )
    return issues


def summarize_issues(issues: list[DetectedIssue]) -> str:
    """Create a compact deterministic summary for the LLM agents."""

    if not issues:
        return "No threshold breaches were detected in the current production dataset."

    critical_count = sum(1 for issue in issues if issue.severity == "critical")
    affected_machines = sorted({issue.machine_id for issue in issues})
    metrics = sorted({issue.metric for issue in issues})
    return (
        f"Detected {len(issues)} issues across {len(affected_machines)} machines. "
        f"Critical issues: {critical_count}. Metrics impacted: {', '.join(metrics)}."
    )


def detect_anomalies(
    df: pd.DataFrame | None = None,
    data: pd.DataFrame | None = None,
    csv_path: str | None = None,
    file_path: str | None = None,
    path: str | None = None,
    *,
    thresholds: ThresholdConfig | None = None,
) -> list[dict[str, Any]]:
    """Public anomaly detection helper used by tests and the data agent."""

    frame = df if df is not None else data
    if frame is None:
        frame = load_production_data(csv_path=csv_path, file_path=file_path, path=path)

    issues = detect_anomaly_models(frame, thresholds=thresholds)
    return [issue.model_dump(mode="json") for issue in issues]
