from __future__ import annotations

import inspect
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Iterable

import pytest


STRICT_OUTPUT_KEYS = {"issues", "analysis", "solutions", "confidence_score"}


def import_first(candidates: Iterable[str]) -> Any:
    """Import the first available module path from candidates."""
    last_error: Exception | None = None
    for path in candidates:
        try:
            return import_module(path)
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = exc
    raise AssertionError(
        f"None of the candidate modules could be imported: {list(candidates)}. "
        f"Last import error: {last_error!r}"
    )


def get_attr_first(obj: Any, names: Iterable[str], *, required: bool = True) -> Any:
    """Return the first matching attribute from an object."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    if required:
        raise AssertionError(
            f"None of the expected attributes were found on {obj}: {list(names)}"
        )
    return None


def call_with_supported_kwargs(func: Any, **kwargs: Any) -> Any:
    """
    Call function using only kwargs it accepts.

    Supports permissive call patterns while still exercising real implementations.
    """
    signature = inspect.signature(func)
    accepts_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in signature.parameters.values()
    )
    if accepts_var_kw:
        return func(**kwargs)

    accepted = {name: value for name, value in kwargs.items() if name in signature.parameters}
    return func(**accepted)


def assert_strict_output_shape(payload: dict[str, Any]) -> None:
    """Assert exact JSON contract required by the project."""
    assert set(payload.keys()) == STRICT_OUTPUT_KEYS
    assert isinstance(payload["issues"], list)
    assert isinstance(payload["analysis"], str)
    assert isinstance(payload["solutions"], list)
    assert isinstance(payload["confidence_score"], (float, int))
    assert 0.0 <= float(payload["confidence_score"]) <= 1.0


@pytest.fixture(autouse=True)
def _disable_live_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Default test safety: avoid accidental live API usage in local/CI test runs.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_csv_path(project_root: Path) -> Path:
    path = project_root / "data" / "production_sample.csv"
    assert path.exists(), f"Expected sample data at {path}"
    return path


@pytest.fixture
def strict_mock_output() -> dict[str, Any]:
    return {
        "issues": [
            {
                "machine_id": "M-009",
                "issue_type": "temperature",
                "severity": "high",
                "value": 101.3,
            }
        ],
        "analysis": "Overheating likely due to cooling loop degradation.",
        "solutions": [
            {
                "priority": 1,
                "action": "Inspect and replace cooling pump",
                "owner": "maintenance",
            }
        ],
        "confidence_score": 0.91,
    }


def pytest_report_header(config: Any) -> list[str]:
    return [
        "Manufacturing analytics tests enforce strict output keys: "
        "issues, analysis, solutions, confidence_score",
        f"OPENAI_API_KEY set for test isolation: {bool(os.getenv('OPENAI_API_KEY'))}",
    ]
