# Third-Party Agent Tooling

## Ponytail
The project-local `.claude/skills/ponytail/` contains a paraphrased project-specific implementation of the minimal-safe-engineering behavior inspired by the MIT-licensed Ponytail project. The full upstream Claude Code plugin is optional and adds lifecycle hooks/modes.

## Graphify
The project-local `.claude/skills/graphify/` defines how this repository should use the external Graphify CLI. `graphifyy` is a developer tool only and is not part of the product runtime. Upstream Graphify is open source and supports project-scoped Claude Code integration.

Always review upstream licenses/versions before vendoring third-party source. This blueprint does not vendor their implementation code.
