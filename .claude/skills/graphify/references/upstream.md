# Upstream Graphify

Project:
- Repository: https://github.com/Graphify-Labs/graphify
- Site: https://graphify.com/
- PyPI package: `graphifyy` (CLI command: `graphify`)
- License: Apache-2.0 / MIT components upstream

Upstream supports project-scoped Claude Code installation:

```bash
uv tool install graphifyy
graphify install --project
```

This blueprint already includes a project-local `graphify` skill and its own Claude routing rules, so running the upstream installer is optional. If it modifies `CLAUDE.md` or `.claude/settings.json`, review the diff and preserve this repository's stricter architecture/security rules.
