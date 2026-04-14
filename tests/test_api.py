from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from conftest import assert_strict_output_shape, import_first
from fastapi.testclient import TestClient

API_MODULE_CANDIDATES = [
    "app.main",
    "main",
    "api.main",
    "app.api.main",
]

WORKFLOW_PATHS = [
    "graph.workflow",
    "app.graph.workflow",
    "workflow",
]

WORKFLOW_FN_CANDIDATES = [
    "run_workflow",
    "execute_workflow",
    "analyze_workflow",
    "analyze_production",
]


@pytest.fixture
def api_app():
    module = import_first(API_MODULE_CANDIDATES)
    assert hasattr(module, "app"), "Expected FastAPI instance named 'app' in API module."
    return module.app


def _patch_workflow_functions(
    monkeypatch: pytest.MonkeyPatch,
    strict_mock_output: dict[str, Any],
) -> None:
    def fake_workflow(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return strict_mock_output

    for path in WORKFLOW_PATHS:
        try:
            workflow_module = __import__(path, fromlist=["*"])
        except Exception:
            continue
        for name in WORKFLOW_FN_CANDIDATES:
            if hasattr(workflow_module, name):
                monkeypatch.setattr(workflow_module, name, fake_workflow)


def test_analyze_endpoint_returns_strict_shape(
    api_app,
    monkeypatch: pytest.MonkeyPatch,
    sample_csv_path,
    strict_mock_output: dict[str, Any],
) -> None:
    _patch_workflow_functions(monkeypatch, strict_mock_output)
    client = TestClient(api_app)

    with sample_csv_path.open("rb") as f:
        file_response = client.post(
            "/analyze",
            files={"file": ("production_sample.csv", f, "text/csv")},
        )

    if file_response.status_code == 200:
        payload = file_response.json()
        assert_strict_output_shape(payload)
        return

    df = pd.read_csv(sample_csv_path)
    json_response = client.post("/analyze", json={"data": df.to_dict(orient="records")})
    assert json_response.status_code == 200, (
        f"Expected 200 from /analyze using file upload or JSON body, got "
        f"{file_response.status_code} and {json_response.status_code}"
    )
    assert_strict_output_shape(json_response.json())
