"""LangGraph orchestration for the manufacturing analytics agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore

from app.agents import DataAnalysisAgent, ReasoningAgent, SolutionAgent, ValidationAgent
from app.config import get_settings
from app.schemas import AnalysisJob, AnalysisResponse, ThresholdConfig


class WorkflowState(TypedDict, total=False):
    """State that flows through the LangGraph workflow."""

    records: list[dict[str, Any]]
    csv_text: str | None
    csv_path: str | None
    source_name: str | None
    thread_id: str
    thresholds: dict[str, Any]
    issues: list[dict[str, Any]]
    issue_summary: str
    plant_snapshot: dict[str, Any]
    analysis: str
    root_causes: list[dict[str, Any]]
    solutions: list[dict[str, Any]]
    confidence_score: float
    validation_notes: list[str]
    final_output: dict[str, Any]


@dataclass
class AgentBundle:
    """Shared agent registry backed by a single long-term memory store."""

    data_agent: DataAnalysisAgent
    reasoning_agent: ReasoningAgent
    solution_agent: SolutionAgent
    validation_agent: ValidationAgent


_STORE = InMemoryStore()
_CHECKPOINTER = InMemorySaver()


@lru_cache(maxsize=1)
def get_agent_bundle() -> AgentBundle:
    settings = get_settings()
    return AgentBundle(
        data_agent=DataAnalysisAgent(settings, _STORE),
        reasoning_agent=ReasoningAgent(settings, _STORE),
        solution_agent=SolutionAgent(settings, _STORE),
        validation_agent=ValidationAgent(settings, _STORE),
    )


def data_analysis_agent(state: WorkflowState) -> dict[str, Any]:
    """First workflow node: load telemetry and detect issues."""

    thresholds = ThresholdConfig.model_validate(state.get("thresholds", {}))
    response = get_agent_bundle().data_agent.run(
        records=state.get("records", []),
        csv_text=state.get("csv_text"),
        csv_path=state.get("csv_path"),
        thresholds=thresholds,
        thread_id=state["thread_id"],
        source_name=state.get("source_name"),
    )
    return {
        "issues": [issue.model_dump(mode="json") for issue in response.issues],
        "issue_summary": response.issue_summary,
        "plant_snapshot": response.plant_snapshot.model_dump(mode="json"),
    }


def reasoning_agent(state: WorkflowState) -> dict[str, Any]:
    """Second workflow node: explain likely root causes."""

    response = get_agent_bundle().reasoning_agent.run(
        issues=state.get("issues", []),
        issue_summary=state.get("issue_summary", ""),
        plant_snapshot=state.get("plant_snapshot", {}),
        thread_id=state["thread_id"],
    )
    return {
        "analysis": response.analysis,
        "root_causes": [cause.model_dump(mode="json") for cause in response.root_causes],
    }


def solution_agent(state: WorkflowState) -> dict[str, Any]:
    """Third workflow node: propose prioritized remediations."""

    response = get_agent_bundle().solution_agent.run(
        issues=state.get("issues", []),
        root_causes=state.get("root_causes", []),
        analysis=state.get("analysis", ""),
        plant_snapshot=state.get("plant_snapshot", {}),
        thread_id=state["thread_id"],
    )
    return {
        "solutions": [solution.model_dump(mode="json") for solution in response.solutions],
    }


def validation_agent(state: WorkflowState) -> dict[str, Any]:
    """Final workflow node: validate the assembled JSON output."""

    response = get_agent_bundle().validation_agent.run(
        issues=state.get("issues", []),
        analysis=state.get("analysis", ""),
        root_causes=state.get("root_causes", []),
        solutions=state.get("solutions", []),
        issue_summary=state.get("issue_summary", ""),
        plant_snapshot=state.get("plant_snapshot", {}),
        thread_id=state["thread_id"],
    )

    final_output = AnalysisResponse(
        issues=[issue.model_dump(mode="json") for issue in response.issues],
        analysis=response.analysis,
        solutions=[solution.model_dump(mode="json") for solution in response.solutions],
        confidence_score=response.confidence_score,
    ).model_dump(mode="json")

    _STORE.put(("manufacturing_reports",), state["thread_id"], final_output)
    return {
        "confidence_score": response.confidence_score,
        "validation_notes": response.validation_notes,
        "final_output": final_output,
    }


def build_workflow():
    """Build the LangGraph workflow for manufacturing analysis."""

    graph = StateGraph(WorkflowState)
    graph.add_node("data_analysis", data_analysis_agent)
    graph.add_node("reasoning", reasoning_agent)
    graph.add_node("solutioning", solution_agent)
    graph.add_node("validation", validation_agent)

    graph.add_edge(START, "data_analysis")
    graph.add_edge("data_analysis", "reasoning")
    graph.add_edge("reasoning", "solutioning")
    graph.add_edge("solutioning", "validation")
    graph.add_edge("validation", END)

    return graph.compile(checkpointer=_CHECKPOINTER, store=_STORE)


def _coerce_job(
    *,
    job: AnalysisJob | None = None,
    csv_path: str | None = None,
    file_path: str | None = None,
    path: str | None = None,
    csv_text: str | None = None,
    records: list[dict[str, Any]] | None = None,
    data: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
    input: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> AnalysisJob:
    """Normalize the different workflow entrypoints into a single AnalysisJob."""

    if job is not None:
        return job

    payload = dict(state or {})
    if input:
        payload.update(input)

    return AnalysisJob(
        records=records or data or payload.get("records") or payload.get("data") or [],
        csv_text=csv_text or payload.get("csv_text"),
        csv_path=csv_path
        or file_path
        or path
        or payload.get("csv_path")
        or payload.get("file_path")
        or payload.get("path"),
        source_name=payload.get("source_name"),
        thread_id=thread_id or payload.get("thread_id"),
        thresholds=payload.get("thresholds") or get_settings().thresholds,
    )


def run_workflow(
    *,
    job: AnalysisJob | None = None,
    csv_path: str | None = None,
    file_path: str | None = None,
    path: str | None = None,
    csv_text: str | None = None,
    records: list[dict[str, Any]] | None = None,
    data: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
    input: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full manufacturing workflow and return strict JSON output."""

    normalized_job = _coerce_job(
        job=job,
        csv_path=csv_path,
        file_path=file_path,
        path=path,
        csv_text=csv_text,
        records=records,
        data=data,
        state=state,
        input=input,
        thread_id=thread_id,
    )

    resolved_thread_id = normalized_job.thread_id or str(uuid4())
    workflow_input: WorkflowState = {
        "records": [record.model_dump(mode="json") for record in normalized_job.records],
        "csv_text": normalized_job.csv_text,
        "csv_path": normalized_job.csv_path,
        "source_name": normalized_job.source_name,
        "thread_id": resolved_thread_id,
        "thresholds": normalized_job.thresholds.model_dump(mode="json"),
    }

    result = build_workflow().invoke(
        workflow_input,
        config={"configurable": {"thread_id": resolved_thread_id}},
    )
    if "final_output" in result:
        return AnalysisResponse.model_validate(result["final_output"]).model_dump(mode="json")

    return AnalysisResponse(
        issues=result.get("issues", []),
        analysis=result.get("analysis", ""),
        solutions=result.get("solutions", []),
        confidence_score=float(result.get("confidence_score", 0.0)),
    ).model_dump(mode="json")


def analyze_production(**kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for tests and external callers."""

    return run_workflow(**kwargs)
