# Security Model

## Threats specific to browser agents
- Prompt injection embedded in target page.
- Data exfiltration through navigation/forms/uploads.
- Destructive clicks.
- Credential leakage in screenshots, logs, HAR or model prompts.
- SSRF-like navigation to internal services.
- Malicious downloads.

## Required controls
- `RunPolicy` with allowed origins and action-class controls (`destructive_actions`, `allow_file_uploads`, `allow_downloads` in `contracts/run-policy.schema.json`).
- **RunPolicy resolution**: un run nunca arranca sin una RunPolicy resuelta con `allowed_origins` (plan → environment default → project default; ver `docs/12-api-and-events.md`).
- Untrusted-content boundary: page text can inform observations, never modify policy/system instructions.
- Tool/action schemas with explicit allowed operations.
- Destructive actions deny-by-default; require policy flag and verification.
- Credentials referenced, not copied into domain logs/events.
- Redaction hooks for logs/artifacts where feasible.
- Browser profile isolated per run/context.
- Upload path allowlist (`upload_path_allowlist` in RunPolicy) cuando `allow_file_uploads` es true.
- Audit trail for every side-effect action.
- Model-call budget: toda RunPolicy acota `max_model_calls`.

## Origin allowlist semantics (normativo)
- Las entradas de `allowed_origins` son **origins** RFC 6454: `scheme://host[:port]`, sin path/query.
- Matching **exacto**: sin subdominios implícitos, sin prefijos de path, scheme-sensitive.
- Cada navigation, redirect y download target se valida contra la allowlist **antes** de la acción; un target fuera de allowlist se bloquea y se registra como evento.
- Memory retrieval nunca amplía la allowlist.

## Credential handling (normativo)
- Los valores de secrets viven fuera de Git (env vars / secret files / futura integración externa). `credential_refs` (PostgreSQL) mapea referencia → ubicación, nunca el valor.
- Una BrowserAction `fill` que necesita un secret lleva `{"credential_ref": "..."}` en lugar de un literal; la referencia se resuelve únicamente dentro del browser adapter en el momento de ejecución.
- Los valores resueltos se marcan no-loggables: se excluyen de action payload persistido, events, artifacts, screenshots anotados y model prompts.
- `storage-state.json` se protege como mínimo con permisos de filesystem restrictivos; el cifrado en reposo es un upgrade path documentado, no un requisito v1.

## Platform identity model (v1)
- v1 es **local-first single-operator**: el API se expone sólo en localhost/red interna de Compose y no exige autenticación de plataforma.
- `tenant` es sinónimo de `project` en v1; los hard filters de retrieval usan project/environment/role.
- Los códigos `AUTH_REQUIRED`/`FORBIDDEN` del CLI envelope y el exit code 3 quedan reservados para token auth futura; introducir auth real requiere ADR.

## Development secrets
Claude Code settings deny reading real `.env` files by default (`.env`, `.env.local`, `.env.development`, `.env.production`, `.env.staging`, `.env.test`); `.env.example` permanece legible y versionado como schema. Use `.env.example` for schema and local secret injection outside commits.


## Adaptive memory poisoning controls
- Todo contenido extraído de la web conserva origen `untrusted`; no puede crear policy/allowlist/credential instructions.
- Redactar secrets/tokens/cookies/passwords antes de crear knowledge candidates.
- Tenant/project/environment/role son hard filters de retrieval, no sugerencias al LLM.
- Hipótesis/root-cause generados por modelo conservan `model_derived=true`; no pueden promocionarse a deterministic facts sin evidence.
- Contradicciones verificadas invalidan o fuerzan revalidation del playbook.
- Memory retrieval no amplía allowed origins/actions y no puede eliminar confirmation/safety requirements.
- Añadir fixtures específicos de prompt injection -> candidate poisoning -> retrieval para demostrar que el ciclo completo resiste contaminación.
