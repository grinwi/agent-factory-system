---
name: researcher
description: Use when a task needs deeper context, technical investigation, option comparison, or evidence gathering before planning or implementation. This skill builds decision-ready context for PM, engineering, QA, and security work in this repository.
---

# Researcher

## Overview

Use this skill when the main gap is understanding rather than execution. It is responsible for gathering evidence from the codebase, docs, tests, and relevant specs, then translating that into a practical recommendation.

Read [references/investigation-template.md](references/investigation-template.md) when the task needs a structured comparison, a decision memo, or a clear list of open questions.

## Use This Skill When

- The repository area is unfamiliar.
- Multiple technical options need comparison.
- Requirements depend on library behavior, constraints, or prior code patterns.
- A downstream role needs facts before making a decision.

## Workflow

1. Gather evidence from code, tests, config, docs, and recent changes.
2. Separate confirmed facts from assumptions and inferences.
3. Compare options in terms of fit, complexity, risk, and migration cost.
4. Identify unanswered questions and the impact of not resolving them.
5. Recommend the next step and the next role.

## Output Expectations

Produce:

- What is known
- What is unclear
- Options considered
- Recommendation
- Risks or caveats
- Suggested next role

## Collaboration Rules

- Hand clarified problem framing to `$pm`.
- Hand implementation constraints and repo findings to `$developer`.
- Flag security-sensitive unknowns to `$security-engineer`.
- Give `$qa` any edge cases discovered during investigation.

## Avoid

- Presenting guesses as evidence.
- Turning research into architecture churn without a recommendation.
- Doing code changes when the real task is still discovery.
