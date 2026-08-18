# Upstream Ponytail

This repository ships a project-specific, paraphrased Ponytail-compatible discipline so it works without a user-level plugin.

Upstream project:
- Repository: https://github.com/DietrichGebert/ponytail
- Site: https://ponytail.dev/
- License: MIT

For the full upstream Claude Code plugin with lifecycle hooks and intensity modes, install it manually inside Claude Code:

```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

The project-local rules remain authoritative where they are stricter, especially Clean Architecture, durability, security and testing requirements.
