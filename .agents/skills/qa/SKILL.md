---
name: qa
description: Use when a change needs test planning, behavioral validation, regression review, or release-readiness assessment. This skill validates implemented work against acceptance criteria and reports findings, gaps, and residual risk.
---

# QA

## Overview

Use this skill to verify that repository changes behave correctly, are covered by tests, and do not introduce obvious regressions. It is especially useful after implementation and before merge or release decisions.

Read [references/test-strategy.md](references/test-strategy.md) when the change is broad, touches multiple layers, or needs a risk-based test plan.

## Use This Skill When

- A feature implementation is ready for validation.
- A bug fix needs regression coverage.
- You need a test plan before or during development.
- You need a release-readiness or confidence assessment.

## Workflow

1. Gather expected behavior from the task, `$pm` acceptance criteria, and developer notes.
2. Identify the highest-risk paths: happy path, edge cases, failure handling, and regressions.
3. Run or review the most relevant tests and commands.
4. Compare observed behavior with expected behavior.
5. Report findings ordered by severity, then note residual risks and test gaps.

## Output Expectations

Produce:

- Test scope
- Findings, if any
- Coverage gaps
- Residual risks
- Go or no-go recommendation

## Collaboration Rules

- Ask `$pm` for acceptance criteria if expected behavior is unclear.
- Ask `$developer` for setup, fixtures, or intended behavior when tests disagree with implementation.
- Pull in `$security-engineer` when QA uncovers risky exposure, unsafe defaults, or abuse paths.

## Avoid

- Calling something "tested" without naming what was actually validated.
- Mixing product feedback with verified defects.
- Burying critical failures under general commentary.
