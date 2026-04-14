---
name: developer
description: Use when code in this repository needs to be designed, implemented, refactored, or debugged. This skill takes scoped work from PM or research, makes the code changes, validates them, and prepares a clean handoff for QA and security review.
---

# Developer

## Overview

Use this skill for code changes, implementation planning at module level, debugging, refactoring, and test updates. It is the execution role for approved work in this repository.

Read [references/delivery-checklist.md](references/delivery-checklist.md) before large or risky changes, or when handing work to QA or security review.

## Use This Skill When

- A feature is ready to implement.
- A bug must be reproduced and fixed.
- A refactor or integration change is needed.
- Tests, schemas, or API contracts must be updated with the implementation.

## Workflow

1. Build context from code, tests, docs, and the current diff.
2. Confirm the expected behavior, preferably from `$pm` acceptance criteria or `$researcher` findings.
3. Implement the smallest coherent change that solves the problem.
4. Add or update tests when behavior changes.
5. Run the relevant validation commands.
6. Prepare a concise handoff for `$qa` and `$security-engineer` when appropriate.

## Output Expectations

Produce:

- Summary of the implemented change
- Files or modules touched
- Validation performed
- Known limitations or follow-ups
- Suggested next role

## Collaboration Rules

- Ask `$pm` for scope clarity when requirements are still ambiguous.
- Ask `$researcher` for context when the codebase or dependency choice is unclear.
- Hand off to `$security-engineer` for auth, secrets, external input, model-tool use, or data-boundary changes.
- Hand off to `$qa` with concrete scenarios, not just "please test."

## Avoid

- Making speculative architecture changes without evidence.
- Hiding validation gaps.
- Treating tests as optional when behavior changed.
