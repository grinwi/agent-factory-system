"""Validation heuristics used by the validation agent."""

from __future__ import annotations

import re
from typing import Any

from app.schemas import DetectedIssue, RootCauseHypothesis, SolutionRecommendation


UNSUPPORTED_TERMS = {"pressure", "torque", "voltage", "humidity"}


def run_consistency_checks(
    *,
    issues: list[DetectedIssue],
    analysis: str,
    root_causes: list[RootCauseHypothesis],
    solutions: list[SolutionRecommendation],
) -> list[str]:
    """Return deterministic findings that the validation agent should resolve."""

    findings: list[str] = []
    known_issue_ids = {issue.issue_id for issue in issues}

    if issues and not root_causes:
        findings.append("Detected issues exist, but no root-cause hypotheses were produced.")
    if issues and not solutions:
        findings.append("Detected issues exist, but no solution recommendations were produced.")
    if not issues and any(solution.priority in {"immediate", "high"} for solution in solutions):
        findings.append("High-priority actions were generated even though no issues were detected.")
    if not analysis.strip():
        findings.append("The reasoning summary is empty.")

    for solution in solutions:
        if not solution.actions:
            findings.append(f"Solution '{solution.title}' is missing action steps.")
        unknown_issue_ids = sorted(
            issue_id for issue_id in solution.related_issue_ids if issue_id not in known_issue_ids
        )
        if unknown_issue_ids:
            findings.append(
                f"Solution '{solution.title}' references unknown issue IDs: "
                + ", ".join(unknown_issue_ids)
                + "."
            )

    return findings


def guard_against_hallucinations(
    *,
    issues: list[DetectedIssue],
    analysis: str,
    root_causes: list[RootCauseHypothesis],
    solutions: list[SolutionRecommendation],
) -> dict[str, Any]:
    """Find unsupported metrics or machine references in the output."""

    findings: list[str] = []
    text_blob = " ".join(
        [
            analysis,
            *(root_cause.title + " " + root_cause.explanation for root_cause in root_causes),
            *(
                solution.title
                + " "
                + solution.rationale
                + " "
                + " ".join(solution.actions)
                + " "
                + solution.expected_impact
                for solution in solutions
            ),
        ]
    ).lower()

    unsupported_terms = sorted(term for term in UNSUPPORTED_TERMS if term in text_blob)
    if unsupported_terms:
        findings.append(
            "Output referenced unsupported operational dimensions: "
            + ", ".join(unsupported_terms)
            + "."
        )

    known_machine_ids = {issue.machine_id for issue in issues}
    mentioned_machine_ids = set(re.findall(r"\bM-\d{3}\b", text_blob.upper()))
    unsupported_machine_ids = sorted(
        machine_id for machine_id in mentioned_machine_ids if machine_id not in known_machine_ids
    )
    if unsupported_machine_ids:
        findings.append(
            "Output referenced machines not present in the evidence set: "
            + ", ".join(unsupported_machine_ids)
            + "."
        )

    return {
        "findings": findings,
        "supported_machine_ids": sorted(known_machine_ids),
        "supported_metrics": ["temperature", "error_rate", "downtime_minutes"],
    }


def suggest_confidence_score(
    *,
    issues: list[DetectedIssue],
    findings: list[str],
    solutions: list[SolutionRecommendation],
    root_causes: list[RootCauseHypothesis],
) -> float:
    """Estimate a bounded confidence score using simple heuristics."""

    score = 0.9 if issues else 0.86
    if issues and solutions and root_causes:
        score += 0.04
    if any(issue.severity == "critical" for issue in issues):
        score -= 0.02

    score -= 0.08 * len(findings)
    return round(min(max(score, 0.1), 0.99), 2)

