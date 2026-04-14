from __future__ import annotations

import pandas as pd

from app.tools.oee import build_oee_summary


def test_build_oee_summary_uses_sample_dataset(sample_csv_path) -> None:
    frame = pd.read_csv(sample_csv_path)

    summary = build_oee_summary(frame)

    assert summary.available is True
    assert summary.source_rows == len(frame)
    assert summary.coverage_rows == len(frame)
    assert summary.overall is not None
    assert 0 < summary.overall.oee <= 1
    assert summary.line_breakdown
    assert summary.line_breakdown[0].oee <= summary.line_breakdown[-1].oee


def test_build_oee_summary_returns_unavailable_without_throughput_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "machine_id": "M-001",
                "temperature": 75.2,
                "error_rate": 0.01,
                "downtime_minutes": 5,
            }
        ]
    )

    summary = build_oee_summary(frame)

    assert summary.available is False
    assert summary.overall is None
    assert "OEE data is unavailable" in summary.narrative
