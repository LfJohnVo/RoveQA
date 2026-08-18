# Phase 04 — Browser Gateway

## Objective
Playwright/Chromium con actions tipadas, evidence provenance y recovery point básico.

## Tasks
1. Crear `test-target-app` determinista.
2. BrowserGateway port y BrowserAction schemas.
3. Playwright adapter con semantic locators y isolation por BrowserContext.
4. Introducir `evidence_set_id` y artifact provenance (`run_id`, step/action identity, target fingerprint/version cuando esté disponible).
5. Capture storage state, screenshots, console/network failures y trace references bajo esa provenance.
6. ArtifactRepository filesystem con streaming/bounded writes y hash/tamaño metadata.
7. PageFingerprint v1.
8. Crash Chromium -> reconstruct context -> verify stable state test.
9. Side-effect test `create record` con verify-before-retry.
10. Integrity test que rechace mezclar artifacts de otro run/evidence set en un manifest.

## Gates
- No arbitrary JS tool expuesto al agente.
- Browser restart recovery demostrado.
- Artifact manifest consistente y con provenance verificable.
- No "latest artifact" lookup puede construir evidencia cross-run por accidente.
- Origin policy enforced.

## Required skills
- `browser-runtime`
- `error-handling-patterns`
- `durability-review`
- `prompt-engineering-patterns` when model-assisted browser decisions are introduced
