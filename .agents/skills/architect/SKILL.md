---
name: architect
description: Use when a feature, refactor, integration, or platform change needs technical structure before implementation. This skill defines system boundaries, module responsibilities, contracts, patterns, and migration shape so development can proceed with fewer design mistakes.
---

# Architect

## Overview

Use this skill when the main challenge is technical design rather than raw coding. It helps shape the implementation approach, especially for cross-module changes, new subsystems, API contracts, extension points, or larger refactors.

Read [references/design-checklist.md](references/design-checklist.md) when the change could affect system boundaries, interfaces, persistence, workflows, or future extensibility.

## Use This Skill When

- A feature spans multiple modules or layers.
- A refactor changes structure, abstractions, or ownership boundaries.
- New APIs, contracts, or internal interfaces are being introduced.
- There are multiple design approaches and the implementation path is not yet stable.
- The repository needs a clean pattern for future extension rather than a one-off patch.

## Workflow

1. Gather the problem framing from `$pm` and the factual context from `$researcher`, when available.
2. Identify the current architecture, affected boundaries, and coupling risks.
3. Compare viable approaches in terms of clarity, complexity, change scope, and future maintainability.
4. Recommend a concrete design: modules, interfaces, data flow, migration steps, and tradeoffs.
5. Hand the design to `$developer` in an implementation-ready form.

## Output Expectations

Produce:

- Design goal
- Current-state constraints
- Recommended architecture or pattern
- Affected modules or boundaries
- Tradeoffs
- Implementation notes for `$developer`
- Suggested next role

## Collaboration Rules

- Use `$researcher` when codebase or dependency context is still incomplete.
- Use `$pm` when scope or acceptance criteria are still unsettled.
- Hand implementation-ready design to `$developer`.
- Involve `$security-engineer` when the design changes trust boundaries, input handling, or exposure surfaces.
- Give `$qa` the risk areas that should shape validation.

## Avoid

- Over-designing small fixes.
- Producing abstract principles without a recommended concrete design.
- Making design choices that ignore the repository’s existing patterns unless there is a clear reason.
