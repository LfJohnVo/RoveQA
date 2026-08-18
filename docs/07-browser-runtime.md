# Browser Runtime

## Interaction ladder
1. Playwright role/label/text locators and accessibility semantics.
2. DOM/structured extraction.
3. Screenshot + VLM fallback.
4. Coordinate interaction only when necessary.

## Typed action set v1
`Navigate`, `Click`, `Fill`, `Select`, `Check`, `Uncheck`, `Upload`, `PressKey`, `WaitFor`, `Extract`, `AssertText`, `AssertUrl`, `Screenshot`, `Back`.

No exponer arbitrary JavaScript como herramienta normal del agente.

## Page fingerprint
Guardar route pattern, title, semantic controls, form signature, DOM/structure hash y visual hash opcional. Un fingerprint conocido puede activar playbook determinista; un cambio obliga revalidación/exploración.

## Artifacts
Por run/step según policy: screenshot WebP/PNG, trace, HAR, console events, network failures, DOM/AX snapshot resumido, video opcional.

## Security
- Origin allowlist por RunPolicy.
- Bloquear navegación/descargas no permitidas.
- Tratar texto web como data; prompt injection no puede cambiar tools/policy/goals.
- Destructive actions off por default y explicitables por policy.
