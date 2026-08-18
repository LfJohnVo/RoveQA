---
name: graphify
description: "Build, refresh and query a project-level knowledge graph of this repository so Claude Code can answer architecture, dependency, impact and code-navigation questions before broad grep/read exploration. Use at repository bootstrap, session/phase orientation, cross-module impact analysis, architectural review, debugging that spans modules, and after structural changes. This is the development-time codebase graph, not the product runtime Graphiti/FalkorDB memory."
---
# Graphify — codebase graph workflow

Use Graphify as Claude Code's structural map of the repository.

## Scope boundary
Keep these systems separate:
- `Graphify`: development-time graph of source code, docs, schemas and configuration for Claude Code.
- `Graphiti + FalkorDB`: product runtime knowledge/experience graph populated by agent executions.

Never couple product domain code to Graphify.

## Bootstrap
1. Check whether `graphify` is available.
2. If missing and tool installation is allowed, prefer:
   ```bash
   uv tool install graphifyy
   ```
3. Do not add `graphifyy` to the application runtime dependencies.
4. Build the initial project graph after the repository skeleton exists:
   ```bash
   graphify .
   ```
5. Keep useful portable graph outputs in `graphify-out/` according to `docs/22-codebase-graph.md`.

## Query-first orientation
When `graphify-out/graph.json` exists, prefer a scoped graph query before broad repository searching for questions such as:
- What modules implement this capability?
- What depends on this port/entity/schema?
- What is the path between API and infrastructure adapter?
- What will this change impact?
- Where does this concept cross backend/frontend/docs?

Examples:
```bash
graphify query "how does a run move from FastAPI to Temporal?"
graphify query "what depends on BrowserGateway?"
graphify path "StartAgentRun" "PlaywrightBrowserGateway"
graphify explain "AgentRun"
```

Use raw file reads after the graph identifies the relevant files or when exact implementation detail is required. The graph is navigation/context, not a substitute for verifying source.

## Refresh discipline
After meaningful structural changes, refresh incrementally:
```bash
graphify update .
```

At each phase gate:
1. Refresh the graph.
2. Query the changed capability and verify the graph matches intended boundaries.
3. Record the refresh/query in `docs/status/HANDOFF.md` when Graphify was available.

If Graphify is unavailable, continue using normal repository tools and record that the graph gate was skipped; do not block correctness solely on this developer aid.

## Confidence discipline
Treat inferred graph relationships as hypotheses until confirmed in source/tests. Use the graph to reduce unnecessary file reads, not to bypass verification.

See `references/upstream.md` and `docs/22-codebase-graph.md`.
