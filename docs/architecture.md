# Architecture Design

## Goal

Build a production-style manufacturing analytics assistant that uses a real LangChain multi-agent architecture, a LangGraph workflow, tool-backed agent steps, basic memory, and a deployable FastAPI interface.

## High-Level Design

The system is a sequential multi-agent pipeline:

1. `DataAnalysisAgent`
   Loads telemetry from CSV or JSON, runs rule-based anomaly detection, and returns a structured issue summary.
2. `ReasoningAgent`
   Consumes the issue summary, uses deterministic heuristics plus LLM reasoning, and outputs root-cause analysis.
3. `SolutionAgent`
   Converts the analyzed issues into prioritized remediation steps.
4. `ValidationAgent`
   Applies consistency checks, basic hallucination guards, and emits the final strict JSON response.

## Why LangGraph

LangGraph is used to model the orchestration layer explicitly:

- Nodes map cleanly to the four domain agents.
- Edges define a deterministic production pipeline.
- Shared store and checkpointing provide basic memory hooks.
- The graph is easy to extend with retry, human review, or branching later.

## Agent Design

### Data Analysis Agent

- LangChain `create_agent`
- Tools:
  - dataset profile loader
  - rule-based anomaly detector
- Output:
  - detected issues
  - issue summary
  - plant snapshot

### Reasoning Agent

- LangChain `create_agent`
- Tools:
  - issue pattern summarizer
  - root-cause hint lookup with recent report memory
- Output:
  - narrative analysis
  - structured root-cause hypotheses

### Solution Agent

- LangChain `create_agent`
- Tools:
  - rule-based solution playbook
  - priority scoring helper with prior-report memory
- Output:
  - prioritized recommendations

### Validation Agent

- LangChain `create_agent`
- Tools:
  - consistency checker
  - hallucination guard
- Output:
  - validated issues
  - validated analysis
  - validated solutions
  - confidence score

## Memory Model

The system uses a shared in-memory LangGraph store keyed by `thread_id`.

- Previous validated reports can be recalled by later requests on the same thread.
- The workflow also compiles with an in-memory checkpointer for request state.
- This keeps the implementation lightweight while still demonstrating real memory plumbing.

## API Layer

FastAPI exposes `POST /analyze` and accepts either:

- multipart CSV upload
- JSON body with production records

The API normalizes the input, runs the workflow, and returns the strict JSON contract:

```json
{
  "issues": [...],
  "analysis": "...",
  "solutions": [...],
  "confidence_score": 0.0
}
```

## Testing Strategy

- Data tests verify loading and anomaly detection against the sample CSV.
- Workflow tests verify agent orchestration order and strict output shape.
- API tests verify `/analyze` for both file and JSON-style request paths without calling a live LLM.

## Extension Points

- Replace in-memory store with Redis or a database-backed store.
- Add human approval between solutioning and validation.
- Introduce richer anomaly detectors or time-series features.
- Add authentication, observability, and persistent audit logs.
