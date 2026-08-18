# Product Spec

## Problema
Crear una plataforma que pueda recorrer aplicaciones web completas, ejecutar acciones, interpretar información y producir evidencia para QA, testing exploratorio, validación de historias de usuario, regresión periódica y automatización de acciones solicitadas por usuarios.

## Casos de uso v1
1. Validar una historia de usuario contra una aplicación implementada.
2. Ejecutar un recorrido QA definido por objetivo, no por script rígido.
3. Explorar periódicamente una aplicación para detectar errores, estados nuevos y oportunidades de mejora.
4. Completar formularios con datos proporcionados o datos sintéticos bajo policy.
5. Reproducir un bug a partir de pasos/texto y generar evidencia.
6. Aprender rutas, fingerprints, transiciones, failure signatures y playbooks de ejecuciones anteriores para reducir razonamiento futuro y refinar estrategias con feedback verificado.
7. Observar en UI un run en vivo y consultar su timeline/evidencias.
8. Pausar/reanudar/cancelar runs largos sin perder progreso durable.
9. Permitir que coding agents y CI creen/ejecuten/verifiquen pruebas por una CLI estable sin automatizar/scrapear la UI humana.
10. Mantener planes de prueba versionados como archivos y producir failure bundles autocontenidos, trazables y consumibles por humanos/agentes.

## No objetivos iniciales
- Navegación móvil nativa.
- Kubernetes/multiregion.
- Fine-tuning continuo automático.
- Automatización irrestricta sobre sitios públicos.
- Sustituir suites deterministas existentes: la plataforma debe complementarlas.
- Depender de un SaaS externo para ejecutar el browser, los modelos o los workflows centrales.
- Convertir la CLI en un segundo runtime de testing: la CLI es un adapter del control plane.

## Actores
- QA engineer: crea runs, historias y analiza findings.
- Product/BA: compara acceptance criteria con comportamiento real.
- Developer: reproduce errores y revisa traces.
- Coding agent: crea/selecciona un TestPlan, ejecuta un run, consume evidencia y vuelve a verificar después de un cambio.
- CI pipeline: ejecuta planes/suites, espera verdicts y publica resultados machine-readable.
- Operator: administra modelos, workers y recursos.

## Contratos públicos v1

### TestPlan
Definición versionable y portable de la intención de una prueba. Debe poder vivir en Git, validarse offline y enviarse por API/CLI sin perder información.

Principios:
- pasos expresan intención/resultado, no CSS/XPath;
- acciones y assertions son explícitas;
- cada plan tiene budget/policy;
- el plan conserva versión/provenance;
- import/export es lossless para el contrato público.

### Run
Instancia durable de ejecución de un TestPlan/historia/exploración. Un timeout del cliente no cambia el lifecycle del run.

Verdicts terminales mínimos:
- `passed`
- `failed`
- `blocked`
- `inconclusive`
- `cancelled`

### FailureBundle
Paquete materializado de una única identidad de evidencia/run. Contiene observación determinista, timeline relevante y artifacts; hipótesis/recomendaciones LLM se etiquetan como model-derived y no se mezclan con hechos observados.

### CLIEnvelope
Contrato versionado para respuestas machine-readable de `roveqa --output json`, con request ID, `data` o error tipado y exit codes estables.

## Principios
- Deterministic first, agentic when needed.
- Semantic browser interaction before vision.
- Evidence before assertion.
- Durable execution by default.
- Client wait is not server cancellation.
- Every remotely retriable mutation is idempotent or verify-before-retry.
- Machine-readable contracts are public API and versioned.
- Deterministic evidence is separated from model hypotheses.
- Untrusted web content never controls policy.
- Learned knowledge is reusable but versioned/invalidatable.
- Learning means evidence-backed memory/playbook refinement, not automatic fine-tuning.
- The runtime knowledge graph is a rebuildable projection; durable candidates/provenance remain in PostgreSQL.
- Local-first/self-hosted remains the default product boundary.
