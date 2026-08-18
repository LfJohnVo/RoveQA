---
name: vercel-react-best-practices
description: Aplica prácticas de rendimiento y arquitectura React inspiradas en las recomendaciones de Vercel al escribir, revisar o refactorizar React/Vite. Usar para componentes, hooks, data fetching, bundles, rendering, listas, effects y optimización.
---
# Vercel React best practices

Aplicar las prácticas relevantes a React + Vite. No introducir APIs o supuestos exclusivos de Next.js.

## Priority order
1. Eliminar waterfalls de datos/trabajo async.
2. Reducir JavaScript enviado y cargado innecesariamente.
3. Evitar renders y subscriptions innecesarios.
4. Mantener data fetching/caching en la capa correcta.
5. Optimizar listas y trabajo costoso sólo cuando exista evidencia.

## Rules
- Iniciar operaciones async independientes en paralelo.
- Usar TanStack Query para server state; no recrear cache/retry/loading con `useEffect` manual.
- Usar `useEffect` para sincronización con sistemas externos, no para estado derivable durante render.
- No duplicar props/server state en state local sin necesidad.
- Preferir state derivado y event handlers a cadenas de effects.
- Mantener dependencias de hooks correctas; no silenciar warnings para ocultar diseño frágil.
- Lazy-load/code-split superficies pesadas que no sean necesarias para el primer render.
- Importar desde módulos específicos cuando reduzca bundle y preserve tree-shaking.
- Virtualizar timelines/logs realmente grandes.
- Evitar memoización indiscriminada; medir o demostrar el costo antes de añadir complejidad.
- Mantener callbacks/objects estables sólo cuando exista un consumidor sensible a identidad.
- No bloquear el main thread con parsing/transformaciones grandes; mover o particionar trabajo cuando corresponda.
- Limpiar listeners, timers y subscriptions en unmount/reconnect.

## Verification
Antes de declarar una optimización terminada, demostrar que preserva comportamiento y ejecutar build/tests. Para cambios de performance relevantes, registrar la medida o evidencia que justificó el cambio.
