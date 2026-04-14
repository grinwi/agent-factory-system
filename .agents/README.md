# Development Agents

This repository includes repo-local development agents as Codex skills under `.agents/skills/`.

## Available Agents

- `$orchestrator`
  Entry point that interprets your request, chooses the right specialists, and controls the handoff flow.
- `$researcher`
  Builds context, compares options, and resolves unknowns before planning or implementation.
- `$pm`
  Shapes work into scoped, delivery-ready feature briefs with acceptance criteria and handoffs.
- `$architect`
  Defines the technical design, boundaries, contracts, and implementation approach for larger changes.
- `$developer`
  Implements scoped changes, updates tests, and prepares engineering handoff notes.
- `$security-engineer`
  Reviews trust boundaries, abuse cases, secrets, model-tool risks, and hardening needs.
- `$qa`
  Validates behavior, reports findings, and assesses residual risk before merge or release.

## How It Works

- `$orchestrator` is the controller.
- The other agents are specialist roles, not independent background processes.
- The orchestrator invokes only the roles needed for the current request.
- Small tasks can stay single-role; larger tasks can move through multiple roles.

## Control Model

The current setup is orchestrated, not autonomous:

- You start with `$orchestrator`.
- `$orchestrator` interprets your request and chooses the smallest useful route.
- Specialist roles are brought in only when their expertise is needed.
- Each specialist returns its result and recommended next role.
- The flow stays human-directed through your prompt and the orchestrator's routing logic.

This means the agents do not keep working independently in the background after you ask once. They act more like a coordinated expert team that is called in on demand, with `$orchestrator` deciding who should contribute next.

If you want true autonomous or parallel workers later, that can be added as a separate automation layer. In that model, `$orchestrator` would translate your request into actual spawned sub-agents and coordinate them programmatically.

## Default Collaboration Flow

Use the full sequence when a feature is ambiguous, risky, or cross-cutting:

1. `$orchestrator` interprets the request and chooses the route.
2. `$researcher` gathers facts and compares options, when needed.
3. `$pm` defines scope, acceptance criteria, and role handoffs, when needed.
4. `$architect` defines the technical design, when needed.
5. `$developer` implements the change and records validation performed.
6. `$security-engineer` reviews the changed trust boundaries and required mitigations, when needed.
7. `$qa` validates behavior, regressions, and residual release risk, when needed.

## When To Skip Or Reorder

- Small, obvious fixes can skip `$pm` and go straight to `$developer`.
- Cross-module or design-heavy work should usually bring in `$architect` before implementation.
- Auth, file handling, external integrations, or LLM/tool changes should bring in `$security-engineer` early.
- Large features can involve `$qa` before implementation to shape the test plan.

## Handoff Contract

Each role should leave behind:

- A short summary of what it learned or changed
- Explicit assumptions
- Risks or open questions
- The recommended next role

## Example Usage

Use `$orchestrator` as the default entry point:

- `$orchestrator add a provider abstraction so this service can switch between OpenAI, Claude, and Gemini cleanly`
- `$orchestrator investigate why /analyze fails on malformed CSV and fix it safely`
- `$orchestrator design and implement a new anomaly rule for vibration spikes`
- `$orchestrator review the file upload path for security risks before we ship`

Use a specialist directly only when you already know the role you want:

- `$architect propose the module boundaries for adding a reporting subsystem`
- `$developer implement the FastAPI endpoint tests for multipart CSV upload`
- `$qa review the current test coverage and list the highest-risk gaps`
