---
name: durability-review
description: Audita workflows, LangGraph state, browser actions, APIs/CLI y persistence para asegurar que ejecuciones de horas sobrevivan crashes, retries y reinicios sin duplicar side effects ni perder progreso. Usar en cambios de Temporal, checkpoints, browser, actions o control de runs.
---
# Durability review $ARGUMENTS

Para cada paso crítico responder:
1. ¿Cuál es la fuente durable de verdad?
2. ¿Qué ocurre si el proceso muere antes de ejecutar?
3. ¿Qué ocurre si muere después del side effect pero antes del ack/checkpoint?
4. ¿Cómo se detecta si el side effect ya ocurrió?
5. ¿Es idempotente o existe verify-before-retry?
6. Si un request mutation pierde su response, ¿repetirlo con la misma idempotency identity devuelve el mismo logical result o crea un duplicate?
7. ¿Qué checkpoint estable permite reconstruir Chromium/worker?
8. ¿Redis puede desaparecer sin perder información imprescindible?
9. ¿Temporal Activity tiene timeout, retry y heartbeat adecuados?
10. ¿LangGraph checkpoint contiene sólo estado necesario y referencias a artifacts, no blobs enormes?
11. ¿Un timeout/Ctrl-C/disconnect del cliente sólo detacha, o puede cancelar accidentalmente el run?
12. ¿Artifacts/failure bundles tienen `run_id`/`evidence_set_id`/version provenance consistente y materialización atómica?
13. ¿Hay una sola capa propietaria de cada retry/rate-limit loop o se multiplican retries entre cliente/API/Temporal?

Proponer tests de crash/retry concretos para cada riesgo encontrado.
