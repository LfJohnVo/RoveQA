# Phase 10 — React MVVM Control UI

## Objective
UI usable para projects, stories y runs en vivo.

## Tasks
0. Consumir el read model/API de Phase 09 para un Knowledge/Memory browser: playbooks, reliability, provenance, version/fingerprint validity y invalidation status; nunca consultar FalkorDB directamente desde frontend.
1. App shell/routing/design tokens mínimos.
2. Project list/detail.
3. Story editor.
4. Run launch form.
5. Run ViewModel con REST baseline + WebSocket realtime.
6. Timeline, current goal/page, findings, artifacts.
7. Pause/resume/cancel commands.
8. Disconnected/reconnecting states.

## Gates
- Views no importan API clients.
- Reload de página reconstruye run desde REST.
- WebSocket reconnect no duplica eventos visuales.
- frontend lint/type/test/build verdes.
## Required skills
- `interface-design`
- `frontend-design`
- `frontend-mvvm-slice`
- `vercel-react-best-practices`

