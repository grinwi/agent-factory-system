"""Deterministic helper rules for reasoning and solution generation."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.schemas import DetectedIssue, PlantSnapshot, SolutionRecommendation

SEVERITY_SCORE = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

PRIORITY_BY_SCORE = {
    4: "immediate",
    3: "high",
    2: "medium",
    1: "low",
}


def issue_pattern_summary(issues: list[DetectedIssue]) -> dict[str, Any]:
    """Summarize issue distribution by metric, severity, and machine."""

    metric_counts = Counter(issue.metric for issue in issues)
    severity_counts = Counter(issue.severity for issue in issues)
    machine_counts = Counter(issue.machine_id for issue in issues)
    return {
        "issue_count": len(issues),
        "by_metric": dict(metric_counts),
        "by_severity": dict(severity_counts),
        "impacted_machines": dict(machine_counts),
        "critical_issue_ids": [
            issue.issue_id for issue in issues if issue.severity == "critical"
        ],
    }


def derive_root_cause_hints(
    issues: list[DetectedIssue],
    plant_snapshot: PlantSnapshot,
) -> list[dict[str, Any]]:
    """Return grounded root-cause hints based on issue combinations."""

    if not issues:
        return [
            {
                "title": "Stable operating envelope",
                "explanation": (
                    "The current batch stayed within configured thresholds for "
                    "temperature, error rate, and downtime."
                ),
                "confidence": 0.92,
                "related_issue_ids": [],
            }
        ]

    metrics_by_machine: dict[str, set[str]] = defaultdict(set)
    issue_ids_by_machine: dict[str, list[str]] = defaultdict(list)
    for issue in issues:
        metrics_by_machine[issue.machine_id].add(issue.metric)
        issue_ids_by_machine[issue.machine_id].append(issue.issue_id)

    hints: list[dict[str, Any]] = []
    for machine_id, metrics in metrics_by_machine.items():
        related_issue_ids = issue_ids_by_machine[machine_id]
        if {"temperature", "downtime_minutes"}.issubset(metrics):
            hints.append(
                {
                    "title": f"Thermal stress causing availability loss on {machine_id}",
                    "explanation": (
                        "Concurrent overheating and downtime usually points to cooling "
                        "degradation, blocked airflow, or lubrication issues."
                    ),
                    "confidence": 0.84,
                    "related_issue_ids": related_issue_ids,
                }
            )
        if {"temperature", "error_rate"}.issubset(metrics):
            hints.append(
                {
                    "title": f"Process drift driven by thermal instability on {machine_id}",
                    "explanation": (
                        "When error rate rises with temperature, the line is often "
                        "experiencing sensor drift, unstable tolerances, or worn tooling."
                    ),
                    "confidence": 0.8,
                    "related_issue_ids": related_issue_ids,
                }
            )

    metric_counts = Counter(issue.metric for issue in issues)
    impacted_machine_count = len({issue.machine_id for issue in issues})

    if metric_counts["error_rate"] >= max(2, impacted_machine_count // 2):
        hints.append(
            {
                "title": "Systemic calibration or material-quality variance",
                "explanation": (
                    "A cluster of error-rate anomalies suggests upstream calibration drift, "
                    "material variance, or inspection misalignment across the cell."
                ),
                "confidence": 0.73,
                "related_issue_ids": [
                    issue.issue_id for issue in issues if issue.metric == "error_rate"
                ],
            }
        )

    if metric_counts["downtime_minutes"] >= 2 or plant_snapshot.total_downtime_minutes > 120:
        hints.append(
            {
                "title": "Preventive maintenance backlog",
                "explanation": (
                    "Elevated downtime across the plant often reflects deferred maintenance, "
                    "slow changeovers, or spare-part bottlenecks."
                ),
                "confidence": 0.68,
                "related_issue_ids": [
                    issue.issue_id for issue in issues if issue.metric == "downtime_minutes"
                ],
            }
        )

    if not hints:
        hints.append(
            {
                "title": "Localized machine degradation",
                "explanation": (
                    "The anomaly pattern is concentrated in a small set of assets, which "
                    "typically indicates machine-specific wear or control drift."
                ),
                "confidence": 0.65,
                "related_issue_ids": [issue.issue_id for issue in issues],
            }
        )

    return hints


def prioritization_rules(issues: list[DetectedIssue]) -> dict[str, Any]:
    """Return deterministic scoring rules to help the solution agent rank actions."""

    max_severity_score = max((SEVERITY_SCORE[issue.severity] for issue in issues), default=1)
    metric_scores = Counter()
    for issue in issues:
        metric_scores[issue.metric] += SEVERITY_SCORE[issue.severity]

    return {
        "severity_weights": SEVERITY_SCORE,
        "metric_priority_scores": dict(metric_scores),
        "top_priority_label": PRIORITY_BY_SCORE[max_severity_score],
    }


def build_solution_playbook(issues: list[DetectedIssue]) -> list[dict[str, Any]]:
    """Generate rule-based recommendations grounded in the current issue set."""

    if not issues:
        recommendation = SolutionRecommendation(
            title="Maintain current operating window",
            priority="low",
            rationale=(
                "No anomalies were detected, so the line can continue with routine monitoring."
            ),
            actions=[
                "Keep preventive maintenance on schedule.",
                "Monitor trend changes for the next production batch.",
            ],
            expected_impact="Sustains stable production without introducing unnecessary change.",
            related_issue_ids=[],
        )
        return [recommendation.model_dump(mode="json")]

    issues_by_metric: dict[str, list[DetectedIssue]] = defaultdict(list)
    for issue in issues:
        issues_by_metric[issue.metric].append(issue)

    playbook: list[dict[str, Any]] = []
    for metric, grouped_issues in issues_by_metric.items():
        max_score = max(SEVERITY_SCORE[issue.severity] for issue in grouped_issues)
        related_issue_ids = [issue.issue_id for issue in grouped_issues]

        if metric == "temperature":
            recommendation = SolutionRecommendation(
                title="Stabilize cooling and thermal load",
                priority=PRIORITY_BY_SCORE[max_score],
                rationale=(
                    "Overheating raises scrap risk and often accelerates unplanned downtime."
                ),
                actions=[
                    (
                        "Inspect coolant flow, fan performance, and ventilation on impacted "
                        "machines."
                    ),
                    (
                        "Reduce operating load until temperatures return below the configured "
                        "threshold."
                    ),
                    "Recalibrate temperature sensors after maintenance is completed.",
                ],
                expected_impact="Reduces overheating risk and restores process stability.",
                related_issue_ids=related_issue_ids,
            )
        elif metric == "error_rate":
            recommendation = SolutionRecommendation(
                title="Recalibrate process controls and quality checks",
                priority=PRIORITY_BY_SCORE[max_score],
                rationale=(
                    "Elevated error rates typically signal process drift, material issues, "
                    "or sensor misalignment."
                ),
                actions=[
                    "Run a calibration pass on the affected line or tooling set.",
                    "Verify material lot quality and inspection station alignment.",
                    "Increase sampling frequency until defect rates normalize.",
                ],
                expected_impact="Lowers defect rates and reduces rework pressure.",
                related_issue_ids=related_issue_ids,
            )
        else:
            recommendation = SolutionRecommendation(
                title="Recover uptime through targeted maintenance",
                priority=PRIORITY_BY_SCORE[max_score],
                rationale=(
                    "Sustained downtime usually means maintenance load or changeover friction "
                    "is growing."
                ),
                actions=[
                    "Inspect the affected assets for recurring stoppage causes.",
                    "Prioritize spare parts and maintenance labor for the impacted machines.",
                    "Review changeover sequencing to remove avoidable idle time.",
                ],
                expected_impact="Improves availability and shortens lost-production windows.",
                related_issue_ids=related_issue_ids,
            )

        playbook.append(recommendation.model_dump(mode="json"))

    playbook.sort(
        key=lambda recommendation: ("immediate", "high", "medium", "low").index(
            recommendation["priority"]
        )
    )
    return playbook
