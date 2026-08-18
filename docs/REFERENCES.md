# Official References

Claude Code:
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/mcp

Core runtime references to consult during implementation:
- Temporal Python SDK documentation
- LangGraph persistence/checkpoint documentation
- Playwright Python documentation
- vLLM serving/structured output documentation
- Graphiti/FalkorDB documentation

Do not pin dependency/image versions from this blueprint without checking compatibility on the actual host. Pin exact versions/digests in the implementation once validated.

Skill design references verified while preparing this blueprint:
- Anthropic Claude Code `frontend-design` plugin: https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design
- Interface Design project: https://interface-design.dev/
- Vercel React Best Practices: https://vercel.com/blog/introducing-react-best-practices
- Vercel agent skills: https://github.com/vercel-labs/agent-skills
- Superpowers process skills (brainstorming/systematic debugging): https://github.com/obra/superpowers

The project-local skill files are intentionally adapted to this architecture rather than copied verbatim from external skills. This keeps Clean Architecture, MVVM, Temporal durability and the React/Vite-only frontend constraints authoritative.

## TestSprite CLI design reference

Reviewed on 2026-08-18 as an architectural/product-interface reference:
- Repository: https://github.com/TestSprite/testsprite-cli
- Vision/scope: https://github.com/TestSprite/testsprite-cli/blob/main/VISION.md
- Agent verification workflow: https://github.com/TestSprite/testsprite-cli/blob/main/skills/testsprite-verify.skill.md
- Declarative plan schema: https://github.com/TestSprite/testsprite-cli/blob/main/schemas/plan.schema.json
- HTTP reliability/idempotency implementation: https://github.com/TestSprite/testsprite-cli/blob/main/src/lib/http.ts
- Failure bundle integrity implementation: https://github.com/TestSprite/testsprite-cli/blob/main/src/lib/bundle.ts

Architectural decision: see `docs/24-testsprite-cli-evaluation.md` and `docs/adr/0007-agent-first-cli-contracts.md`.

The TestSprite repository is Apache-2.0, but this blueprint deliberately adopts **patterns and public-interface lessons only**. No TestSprite source is vendored/copied. Any future source-derived implementation requires a dedicated attribution/LICENSE/NOTICE review.


## Adaptive memory graph references verified 2026-08-18
- Graphiti repository / supported graph backends and injectable clients: https://github.com/getzep/graphiti
- FalkorDB Graphiti agentic memory docs: https://docs.falkordb.com/agentic-memory/graphiti.html
- FalkorDB agentic memory overview: https://docs.falkordb.com/agentic-memory/
- vLLM embedding/pooling models and OpenAI-compatible `/v1/embeddings`: https://docs.vllm.ai/en/stable/models/pooling_models/embed/

Implementation note: Graphiti defaults to OpenAI clients when no LLM/embedder is supplied. RoveQA must inject local/configured clients explicitly.
