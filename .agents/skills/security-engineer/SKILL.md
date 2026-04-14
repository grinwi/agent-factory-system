---
name: security-engineer
description: Use when work in this repository touches auth, secrets, external input, file handling, model or tool use, network boundaries, dependencies, or sensitive data. This skill reviews abuse cases, trust boundaries, and mitigations before features ship.
---

# Security Engineer

## Overview

Use this skill to review security posture for new or changed behavior in the repository. It focuses on realistic risks, secure defaults, and concrete mitigations instead of generic warnings.

Read [references/security-review-checklist.md](references/security-review-checklist.md) when reviewing endpoints, uploads, LLM integrations, credentials, or third-party dependencies.

## Use This Skill When

- New endpoints or input surfaces are added.
- CSV, JSON, file upload, or file parsing behavior changes.
- Model provider integration, prompt composition, or tool access changes.
- Secrets, auth, permissions, or data exposure rules change.
- A dependency or external service is introduced.

## Workflow

1. Identify assets, trust boundaries, and attacker-controlled input.
2. Review authentication, authorization, validation, output handling, and logging.
3. Check dependency, secret, and configuration impact.
4. For LLM features, inspect prompt injection, tool misuse, data leakage, and unsafe automation paths.
5. Report issues by severity and provide concrete mitigations or safe defaults.

## Output Expectations

Produce:

- Threat summary
- Findings ordered by severity
- Required fixes before merge
- Recommended hardening steps
- Residual risk

## Collaboration Rules

- Ask `$researcher` for dependency or platform context when needed.
- Ask `$developer` for actual data flows and trust-boundary details.
- Feed must-fix items back before QA signoff.
- Tell `$qa` which abuse cases or negative tests should be covered.

## Avoid

- Listing generic best practices without tying them to repository changes.
- Treating theoretical issues as urgent without an exploitation path.
- Approving risky changes without naming the residual risk.
