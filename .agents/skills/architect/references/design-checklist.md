# Design Checklist

## Problem and Scope

- What problem must the design solve?
- What is intentionally out of scope?
- What constraints come from product, ops, or the existing codebase?

## Boundaries

- Which modules, services, or layers are affected?
- Where should responsibilities live?
- What interfaces or contracts need to change?

## Tradeoffs

- What is the simplest viable approach?
- What coupling or migration cost does each option introduce?
- What future extension points matter here?

## Handoff

- What should `$developer` implement first?
- What should `$security-engineer` review?
- What should `$qa` validate?
