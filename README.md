# Manufacturing Analytics Multi-Agent System

Production-style LangChain and LangGraph backend that analyzes manufacturing telemetry, explains issues, proposes actions, and returns strict JSON through a FastAPI API.

## Architecture

The system is organized as a real multi-agent pipeline:

1. `DataAnalysisAgent` loads CSV/JSON production data with pandas and runs deterministic anomaly detection.
2. `ReasoningAgent` interprets the issue set and produces grounded root-cause analysis.
3. `SolutionAgent` proposes prioritized remediation steps.
4. `ValidationAgent` checks consistency, applies basic hallucination guards, and emits the final JSON response.

The agents are orchestrated with LangGraph in [`app/graph/workflow.py`](/Users/adam.grunwald/agent-factory-system/app/graph/workflow.py). Each agent is built with LangChain `create_agent`, real tools, structured outputs, and shared in-memory storage for basic memory between requests on the same `thread_id`.

## Project Layout

- [`app/agents`](/Users/adam.grunwald/agent-factory-system/app/agents)
- [`app/api`](/Users/adam.grunwald/agent-factory-system/app/api)
- [`app/data`](/Users/adam.grunwald/agent-factory-system/app/data)
- [`app/graph`](/Users/adam.grunwald/agent-factory-system/app/graph)
- [`app/tools`](/Users/adam.grunwald/agent-factory-system/app/tools)
- [`tests`](/Users/adam.grunwald/agent-factory-system/tests)
- [`data/production_sample.csv`](/Users/adam.grunwald/agent-factory-system/data/production_sample.csv)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## API

`POST /analyze`

Supported inputs:

- `multipart/form-data` with `file=<csv>`
- `application/json` with `records` or `data`

Example JSON body:

```json
{
  "records": [
    {
      "machine_id": "M-009",
      "temperature": 101.3,
      "error_rate": 0.042,
      "downtime_minutes": 48
    }
  ],
  "thread_id": "demo-line-a"
}
```

Response shape:

```json
{
  "issues": [],
  "analysis": "string",
  "solutions": [],
  "confidence_score": 0.92
}
```

## Dev Workflow

```bash
pytest
ruff check .
docker compose up --build
```

More detail is in [`docs/architecture.md`](/Users/adam.grunwald/agent-factory-system/docs/architecture.md).

