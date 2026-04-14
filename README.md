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

## Easy Local Setup

For less technical testers, the project now includes a guided local setup wizard.

1. Download or clone the repository from GitHub.
2. Start the wizard:

```bash
python3 scripts/bootstrap.py
```

On macOS you can also run [`setup.command`](/Users/adam.grunwald/agent-factory-system/setup.command), and on Windows you can run [`setup.bat`](/Users/adam.grunwald/agent-factory-system/setup.bat).

The wizard will:

- create a local `.venv`
- install the app dependencies
- ask which provider you want to use: OpenAI, Claude, or Gemini
- store your key only in the local `.env`
- offer to start the web app automatically

The first setup run needs an internet connection so Python can install the required packages.

After setup, launch the app again with:

```bash
python3 scripts/run_local.py
```

Or use [`start.command`](/Users/adam.grunwald/agent-factory-system/start.command) on macOS or [`start.bat`](/Users/adam.grunwald/agent-factory-system/start.bat) on Windows.

The local launcher opens `http://127.0.0.1:8000/` in your browser and keeps your API key on your machine.

## Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/` for the web console, or use `http://localhost:8000/docs` for the API docs.

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

If you omit `LLM_MODEL`, the app falls back to a provider-specific default from [`.env.example`](/Users/adam.grunwald/agent-factory-system/.env.example).

The app automatically loads [`.env`](/Users/adam.grunwald/agent-factory-system/.env) from the project root, so local users do not need to export environment variables manually.

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

## Web UI

The app now ships with a lightweight browser UI at `/`.

- Upload a production CSV from the browser
- Inspect dashboard cards and chart-style visual breakdowns
- Review the generated root-cause analysis and recommended actions
- Download a PDF report built from the dashboard payload

Additional human-facing endpoints:

- `POST /analyze/dashboard`
- `POST /reports/pdf`

## Dev Workflow

```bash
pytest
ruff check .
docker compose up --build
```

More detail is in [`docs/architecture.md`](/Users/adam.grunwald/agent-factory-system/docs/architecture.md).
