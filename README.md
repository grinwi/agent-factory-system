# Manufacturing Analytics Multi-Agent System

Production-style LangChain and LangGraph backend that analyzes manufacturing telemetry, explains issues, proposes actions, and returns strict JSON through a FastAPI API.

The agent runtime can be configured to use OpenAI, Anthropic Claude, or Google Gemini through environment variables.

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
- [`.agents`](/Users/adam.grunwald/agent-factory-system/.agents)
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

## Model Providers

Set `LLM_PROVIDER` to one of:

- `openai`
- `anthropic` or `claude`
- `gemini` or `google`

Examples:

```bash
# OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=...
export LLM_MODEL=gpt-4.1-mini

# Claude
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=...
export LLM_MODEL=claude-haiku-4-5-20251001

# Gemini
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=...
export LLM_MODEL=gemini-2.5-flash
```

If you omit `LLM_MODEL`, the app falls back to a provider-specific default from `.env.example`.

## Development Agents

Repo-local development agents are configured as skills in [`.agents/skills`](/Users/adam.grunwald/agent-factory-system/.agents/skills). The team roster and default collaboration flow are documented in [`.agents/README.md`](/Users/adam.grunwald/agent-factory-system/.agents/README.md).

Use `$orchestrator` as the default entry point for development work. It routes requests to the specialist roles, including `$architect` for design-heavy changes, instead of treating every role as an always-on independent process.

The current repository setup is orchestrated and human-in-the-loop: `$orchestrator` decides which specialist should contribute next, but the specialist roles are not autonomous background daemons. If you want, this can later be extended into a deeper automation layer that programmatically spawns and coordinates independent workers.

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
