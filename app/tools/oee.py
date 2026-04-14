"""Overall equipment effectiveness calculations for automotive-style datasets."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from app.schemas import DashboardStatus, OeeInsight, OeeLineInsight, OeeSummary
from app.tools.data_loader import normalize_dataframe

OEE_REQUIRED_COLUMNS: tuple[str, ...] = (
    "planned_production_minutes",
    "good_units",
    "reject_units",
    "ideal_cycle_time_seconds",
)
OEE_BENCHMARK = 0.85
OEE_WATCH_THRESHOLD = 0.7


def build_oee_summary(frame: pd.DataFrame) -> OeeSummary:
    """Build overall and by-line OEE summaries when the dataset supports it."""

    normalized = normalize_dataframe(frame)
    source_rows = int(len(normalized))

    if not _supports_oee(normalized.columns):
        return OeeSummary(
            available=False,
            source_rows=source_rows,
            coverage_rows=0,
            benchmark=OEE_BENCHMARK,
            narrative=(
                "OEE data is unavailable for this upload. Add "
                "`planned_production_minutes`, `good_units`, `reject_units`, and "
                "`ideal_cycle_time_seconds` columns to calculate availability, "
                "performance, and quality."
            ),
        )

    oee_frame = normalized.copy()
    for column in OEE_REQUIRED_COLUMNS:
        oee_frame[column] = pd.to_numeric(oee_frame[column], errors="coerce")

    valid_rows = oee_frame.dropna(subset=list(OEE_REQUIRED_COLUMNS)).copy()
    valid_rows = valid_rows[
        (valid_rows["planned_production_minutes"] > 0)
        & (valid_rows["ideal_cycle_time_seconds"] > 0)
        & (valid_rows["good_units"] >= 0)
        & (valid_rows["reject_units"] >= 0)
    ]

    coverage_rows = int(len(valid_rows))
    if valid_rows.empty:
        return OeeSummary(
            available=False,
            source_rows=source_rows,
            coverage_rows=0,
            benchmark=OEE_BENCHMARK,
            narrative=(
                "OEE columns were detected, but none of the rows contained a complete "
                "valid throughput record."
            ),
        )

    overall = _aggregate_scope(valid_rows)
    line_breakdown: list[OeeLineInsight] = []
    if "line_id" in valid_rows.columns:
        valid_rows["line_id"] = (
            valid_rows["line_id"].fillna("Unassigned line").astype(str).str.strip()
        )
        valid_rows.loc[valid_rows["line_id"] == "", "line_id"] = "Unassigned line"
        line_breakdown = [
            OeeLineInsight(
                line_id=str(line_id),
                machine_count=int(group["machine_id"].nunique()),
                **_aggregate_scope(group).model_dump(mode="json"),
            )
            for line_id, group in valid_rows.groupby("line_id", sort=True)
        ]
        line_breakdown.sort(key=lambda line: (line.oee, line.availability, line.performance))

    return OeeSummary(
        available=True,
        source_rows=source_rows,
        coverage_rows=coverage_rows,
        benchmark=OEE_BENCHMARK,
        narrative=_build_oee_narrative(overall, line_breakdown, coverage_rows, source_rows),
        overall=overall,
        line_breakdown=line_breakdown,
    )


def _supports_oee(columns: Sequence[str]) -> bool:
    return set(OEE_REQUIRED_COLUMNS).issubset(columns)


def _aggregate_scope(frame: pd.DataFrame) -> OeeInsight:
    planned_minutes = float(frame["planned_production_minutes"].sum())
    downtime_minutes = float(frame["downtime_minutes"].sum())
    operating_minutes = max(planned_minutes - downtime_minutes, 0.0)

    good_units = int(round(float(frame["good_units"].sum())))
    reject_units = int(round(float(frame["reject_units"].sum())))
    total_units = max(good_units + reject_units, 0)

    theoretical_runtime_seconds = float(
        ((frame["good_units"] + frame["reject_units"]) * frame["ideal_cycle_time_seconds"]).sum()
    )

    availability = _clamp_ratio(
        operating_minutes / planned_minutes if planned_minutes > 0 else 0.0
    )
    performance = _clamp_ratio(
        theoretical_runtime_seconds / (operating_minutes * 60)
        if operating_minutes > 0
        else 0.0
    )
    quality = _clamp_ratio(good_units / total_units if total_units > 0 else 0.0)
    oee = round(availability * performance * quality, 4)

    return OeeInsight(
        availability=availability,
        performance=performance,
        quality=quality,
        oee=oee,
        planned_production_minutes=round(planned_minutes, 2),
        operating_minutes=round(operating_minutes, 2),
        downtime_minutes=round(downtime_minutes, 2),
        total_units=total_units,
        good_units=good_units,
        reject_units=reject_units,
        status=_status_for_oee(oee),
    )


def _build_oee_narrative(
    overall: OeeInsight,
    line_breakdown: list[OeeLineInsight],
    coverage_rows: int,
    source_rows: int,
) -> str:
    weakest_component = min(
        (
            ("availability", overall.availability),
            ("performance", overall.performance),
            ("quality", overall.quality),
        ),
        key=lambda item: item[1],
    )[0]
    weakest_line = line_breakdown[0] if line_breakdown else None
    benchmark_gap = max(OEE_BENCHMARK - overall.oee, 0.0)

    parts = [
        (
            f"Computed OEE from {coverage_rows} of {source_rows} telemetry rows. "
            f"Overall OEE is {overall.oee * 100:.1f}%."
        ),
        (
            f"The largest loss is in {weakest_component}, with availability at "
            f"{overall.availability * 100:.1f}%, performance at {overall.performance * 100:.1f}%, "
            f"and quality at {overall.quality * 100:.1f}%."
        ),
    ]

    if benchmark_gap > 0:
        parts.append(
            f"This is {benchmark_gap * 100:.1f} points below the 85% world-class benchmark."
        )
    else:
        parts.append("This meets or exceeds the 85% world-class benchmark.")

    if weakest_line is not None:
        parts.append(
            f"The lowest-performing line is {weakest_line.line_id} at "
            f"{weakest_line.oee * 100:.1f}% OEE."
        )

    return " ".join(parts)


def _clamp_ratio(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 4)


def _status_for_oee(oee: float) -> DashboardStatus:
    if oee >= OEE_BENCHMARK:
        return "stable"
    if oee >= OEE_WATCH_THRESHOLD:
        return "watch"
    return "alert"
