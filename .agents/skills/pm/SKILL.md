---
name: pm
description: Use when a feature, bug fix, or technical initiative needs product framing, scope control, acceptance criteria, sequencing, or explicit handoff notes for engineering, QA, security, and research. This skill turns ambiguous requests into delivery-ready work.
---

# PM

## Overview

Use this skill to turn ideas into a clear delivery plan for the repository. It is strongest when the request is still fuzzy, has multiple implementation paths, or needs explicit success criteria before code work starts.

Read [references/handoff-template.md](references/handoff-template.md) when the task needs a formal feature brief or a structured cross-role handoff.

## Use This Skill When

- The request is vague and needs a sharper problem statement.
- A feature should be split into MVP, follow-up work, and non-goals.
- Acceptance criteria, rollout notes, or sequencing are missing.
- Research, security, QA, or implementation work needs explicit owners and questions.

## Workflow

1. Build context from the user request, repository state, existing docs, and any recent diffs.
2. Restate the problem in user or operator terms, not just technical terms.
3. Define goals, non-goals, constraints, dependencies, and open questions.
4. Break the work into a delivery shape that engineering can execute.
5. Write handoff notes for `$researcher`, `$developer`, `$security-engineer`, and `$qa` as needed.

## Output Expectations

Produce a compact feature brief with:

- Problem statement
- Target outcome
- In scope
- Out of scope
- Acceptance criteria
- Risks and dependencies
- Recommended next role

## Collaboration Rules

- Ask `$researcher` to build context when important facts are still unknown.
- Hand implementation-ready scope to `$developer` once the work is clear.
- Pull in `$security-engineer` early for auth, external integrations, file handling, or sensitive data.
- Give `$qa` explicit scenarios and acceptance criteria instead of general statements like "test this."

## Avoid

- Writing implementation details when the real gap is scope clarity.
- Treating assumptions as confirmed facts.
- Passing vague requests downstream without acceptance criteria.
