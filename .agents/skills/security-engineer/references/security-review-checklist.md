# Security Review Checklist

## Input and Boundary Review

- What input is attacker-controlled?
- What files or payloads are accepted?
- Is parsing bounded, validated, and failure-safe?

## Access and Data Review

- Is auth required?
- Is authorization enforced at the right boundary?
- Could sensitive data leak through logs, errors, or model prompts?

## LLM and Tooling Review

- Can untrusted input influence prompts?
- Can the model trigger tools or actions with unsafe context?
- Are external providers given more data than necessary?

## Dependency and Config Review

- Are new libraries or providers necessary?
- Are secrets handled through config instead of code?
- Are safe defaults in place for local and production use?
