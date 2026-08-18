# Security Model

## Threats specific to browser agents
- Prompt injection embedded in target page.
- Data exfiltration through navigation/forms/uploads.
- Destructive clicks.
- Credential leakage in screenshots, logs, HAR or model prompts.
- SSRF-like navigation to internal services.
- Malicious downloads.

## Required controls
- `RunPolicy` with allowed origins/domains and action classes.
- Untrusted-content boundary: page text can inform observations, never modify policy/system instructions.
- Tool/action schemas with explicit allowed operations.
- Destructive actions deny-by-default; require policy flag and verification.
- Credentials referenced, not copied into domain logs/events.
- Redaction hooks for logs/artifacts where feasible.
- Browser profile isolated per run/context.
- Upload path allowlist.
- Audit trail for every side-effect action.

## Development secrets
Claude Code settings deny reading `.env` by default. Use `.env.example` for schema and local secret injection outside commits.


## Adaptive memory poisoning controls
- Todo contenido extraído de la web conserva origen `untrusted`; no puede crear policy/allowlist/credential instructions.
- Redactar secrets/tokens/cookies/passwords antes de crear knowledge candidates.
- Tenant/project/environment/role son hard filters de retrieval, no sugerencias al LLM.
- Hipótesis/root-cause generados por modelo conservan `model_derived=true`; no pueden promocionarse a deterministic facts sin evidence.
- Contradicciones verificadas invalidan o fuerzan revalidation del playbook.
- Memory retrieval no amplía allowed origins/actions y no puede eliminar confirmation/safety requirements.
- Añadir fixtures específicos de prompt injection -> candidate poisoning -> retrieval para demostrar que el ciclo completo resiste contaminación.
