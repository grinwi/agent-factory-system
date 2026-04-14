from __future__ import annotations

from typing import Any

import pytest

from conftest import (
    assert_strict_output_shape,
    call_with_supported_kwargs,
    get_attr_first,
    import_first,
)


WORKFLOW_MODULE_CANDIDATES = [
    "graph.workflow",
    "app.graph.workflow",
    "workflow",
]

BUILD_FN_CANDIDATES = ["build_workflow", "create_workflow", "get_workflow"]
RUN_FN_CANDIDATES = [
    "run_workflow",
    "execute_workflow",
    "analyze_workflow",
    "analyze_production",
]

DATA_NODE_NAMES = ["data_analysis_agent", "data_agent", "run_data_analysis", "data_node"]
REASON_NODE_NAMES = ["reasoning_agent", "run_reasoning", "reasoning_node"]
SOLUTION_NODE_NAMES = ["solution_agent", "run_solutioning", "solution_node"]
VALIDATION_NODE_NAMES = ["validation_agent", "run_validation", "validation_node"]


def _patch_node_if_present(monkeypatch: pytest.MonkeyPatch, module: Any, names: list[str], fn: Any) -> bool:
    for name in names:
        if hasattr(module, name):
            monkeypatch.setattr(module, name, fn)
            return True
    return False


def test_workflow_orchestrates_agents_in_expected_order(
    monkeypatch: pytest.MonkeyPatch, sample_csv_path
) -> None:
    module = import_first(WORKFLOW_MODULE_CANDIDATES)
    call_order: list[str] = []

    def fake_data_agent(state: dict[str, Any]) -> dict[str, Any]:
        call_order.append("data")
        state = dict(state)
        state["issues"] = [{"machine_id": "M-009", "issue_type": "temperature"}]
        return state

    def fake_reasoning_agent(state: dict[str, Any]) -> dict[str, Any]:
        call_order.append("reasoning")
        state = dict(state)
        state["analysis"] = "Root cause indicates cooling failure."
        return state

    def fake_solution_agent(state: dict[str, Any]) -> dict[str, Any]:
        call_order.append("solution")
        state = dict(state)
        state["solutions"] = [{"priority": 1, "action": "Inspect coolant lines"}]
        return state

    def fake_validation_agent(state: dict[str, Any]) -> dict[str, Any]:
        call_order.append("validation")
        return {
            "issues": state.get("issues", []),
            "analysis": state.get("analysis", ""),
            "solutions": state.get("solutions", []),
            "confidence_score": 0.87,
        }

    patched = [
        _patch_node_if_present(monkeypatch, module, DATA_NODE_NAMES, fake_data_agent),
        _patch_node_if_present(monkeypatch, module, REASON_NODE_NAMES, fake_reasoning_agent),
        _patch_node_if_present(monkeypatch, module, SOLUTION_NODE_NAMES, fake_solution_agent),
        _patch_node_if_present(monkeypatch, module, VALIDATION_NODE_NAMES, fake_validation_agent),
    ]
    assert any(patched), (
        "Workflow module did not expose patchable agent-node functions. "
        "Expected at least one of the known names."
    )

    run_fn = get_attr_first(module, RUN_FN_CANDIDATES, required=False)
    if run_fn is not None:
        result = call_with_supported_kwargs(
            run_fn,
            csv_path=str(sample_csv_path),
            file_path=str(sample_csv_path),
            path=str(sample_csv_path),
            state={"csv_path": str(sample_csv_path)},
            input={"csv_path": str(sample_csv_path)},
        )
    else:
        build_fn = get_attr_first(module, BUILD_FN_CANDIDATES)
        workflow = call_with_supported_kwargs(build_fn)
        invoke_fn = get_attr_first(workflow, ["invoke"])
        result = invoke_fn({"csv_path": str(sample_csv_path)})

    assert isinstance(result, dict), "Workflow run must return a dictionary payload."
    assert_strict_output_shape(result)
    assert call_order, "At least one orchestrated stage should have been called."
