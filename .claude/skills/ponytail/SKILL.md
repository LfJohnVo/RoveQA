---
name: ponytail
description: "Enforce minimal safe implementation on coding work: understand the real flow first, reuse existing code, prefer stdlib/native platform/already-installed dependencies, avoid speculative abstractions and keep diffs small without weakening correctness, security, accessibility, error handling, Clean Architecture, MVVM or durability. Use on every implementation, refactor, fix or code review in this repository."
---
# Ponytail — minimal safe engineering

Treat this discipline as always active for code changes.

## Decision ladder
Before adding code, follow this order and stop at the first option that fully satisfies the requirement:
1. Confirm the requested behavior is actually needed by the current phase/spec.
2. Search for an existing implementation or pattern in this repository; reuse it.
3. Prefer the language standard library.
4. Prefer a native platform/framework capability.
5. Prefer an already-installed dependency.
6. Prefer the smallest clear implementation.
7. Add a new abstraction/dependency only when present requirements justify it.

## Project-specific guardrails
Minimalism must never remove required architecture or safety. Do not simplify away:
- Clean Architecture dependency direction.
- MVVM boundaries in React.
- Temporal durability or LangGraph checkpoints.
- idempotency / verify-before-retry for side effects.
- input validation, authorization, secrets protection or prompt-injection defenses.
- meaningful error handling, accessibility or tests.

A short implementation in the wrong layer is not simpler. Fix the root cause at the narrowest shared boundary that owns it.

## Review behavior
When reviewing a diff, actively look for:
- duplicate helpers or models;
- one-implementation interfaces that are not architectural ports;
- premature factories/configuration/plugin systems;
- new dependencies for trivial behavior;
- wrappers that only rename an existing API;
- files/classes created only for hypothetical future use;
- duplicated guards that belong at one shared boundary.

Prefer deletion and reuse over new code when behavior remains correct.

## Output discipline
For implementation work, keep explanations proportional to the change. Document architecture decisions only when they are structurally significant or required by the phase/ADR workflow.

See `references/upstream.md` for the upstream Ponytail project and optional plugin installation.
