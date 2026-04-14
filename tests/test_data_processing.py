from __future__ import annotations

from typing import Any

import pandas as pd
from conftest import call_with_supported_kwargs, get_attr_first, import_first

DATA_MODULE_CANDIDATES = [
    "tools.data_processing",
    "app.tools.data_processing",
    "tools.anomaly_detection",
    "app.tools.anomaly_detection",
    "agents.data_agent",
    "app.agents.data_agent",
]

LOAD_FN_CANDIDATES = [
    "load_csv",
    "load_data",
    "load_production_data",
    "read_production_data",
]

ANOMALY_FN_CANDIDATES = [
    "detect_anomalies",
    "find_anomalies",
    "analyze_anomalies",
    "run_anomaly_detection",
]


def _normalize_issues(result: Any) -> list[Any]:
    if isinstance(result, dict) and "issues" in result:
        issues = result["issues"]
    else:
        issues = result
    assert isinstance(
        issues, list
    ), "Anomaly function must return a list or dict with 'issues' list."
    return issues


def _issue_text(issue: Any) -> str:
    if isinstance(issue, dict):
        return " ".join(str(v) for v in issue.values()).lower()
    return str(issue).lower()


def test_sample_csv_has_expected_columns(sample_csv_path) -> None:
    df = pd.read_csv(sample_csv_path)
    required = {"machine_id", "temperature", "error_rate", "downtime_minutes"}
    assert required.issubset(df.columns)
    assert len(df) >= 20


def test_data_loader_and_anomaly_detection_contract(sample_csv_path) -> None:
    module = import_first(DATA_MODULE_CANDIDATES)
    detect_fn = get_attr_first(module, ANOMALY_FN_CANDIDATES)
    load_fn = get_attr_first(module, LOAD_FN_CANDIDATES, required=False)

    if load_fn:
        loaded = call_with_supported_kwargs(
            load_fn,
            csv_path=str(sample_csv_path),
            file_path=str(sample_csv_path),
            path=str(sample_csv_path),
        )
        assert isinstance(loaded, pd.DataFrame), "Data loader must return pandas DataFrame."
        df = loaded
    else:
        df = pd.read_csv(sample_csv_path)

    issues = _normalize_issues(
        call_with_supported_kwargs(
            detect_fn,
            df=df,
            data=df,
            csv_path=str(sample_csv_path),
            file_path=str(sample_csv_path),
            path=str(sample_csv_path),
        )
    )

    assert issues, "Expected anomaly detection to find at least one issue in sample data."
    issue_blob = " ".join(_issue_text(i) for i in issues)
    assert any(token in issue_blob for token in ["temp", "temperature"])
    assert any(token in issue_blob for token in ["error", "error_rate"])
    assert any(token in issue_blob for token in ["downtime", "down_time"])
