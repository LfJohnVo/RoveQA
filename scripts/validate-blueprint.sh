#!/usr/bin/env bash
set -euo pipefail

required=(
  CLAUDE.md
  README.md
  docs/00-product-spec.md
  docs/01-architecture.md
  docs/17-implementation-roadmap.md
  docs/21-claude-skill-routing.md
  docs/24-testsprite-cli-evaluation.md
  docs/25-agent-first-cli.md
  docs/26-adaptive-learning-graph.md
  docs/adr/0007-agent-first-cli-contracts.md
  docs/adr/0008-adaptive-learning-graph.md
  docs/status/PROGRESS.md
  docs/status/HANDOFF.md
  plans/phase-08-agent-first-cli.md
  plans/phase-14-release-candidate.md
  .claude/settings.json
  .claude/rules/cli.md
  .claude/rules/knowledge.md
  .claude/agents/cli-engineer.md
  .claude/agents/knowledge-engineer.md
  .claude/skills/implement-phase/SKILL.md
  .claude/skills/adaptive-memory-graph/SKILL.md
  .claude/skills/architecture-guard/SKILL.md
  .claude/skills/durability-review/SKILL.md
  .claude/skills/frontend-design/SKILL.md
  .claude/skills/interface-design/SKILL.md
  .claude/skills/vercel-react-best-practices/SKILL.md
  .claude/skills/brainstorming/SKILL.md
  .claude/skills/systematic-debugging/SKILL.md
  .claude/skills/changelog-generator/SKILL.md
  .claude/skills/api-design-principles/SKILL.md
  .claude/skills/error-handling-patterns/SKILL.md
  .claude/skills/postgresql/SKILL.md
  .claude/skills/prompt-engineering-patterns/SKILL.md
  .claude/skills/ponytail/SKILL.md
  .claude/skills/graphify/SKILL.md
  templates/INTERFACE_SYSTEM_TEMPLATE.md
  contracts/test-plan.schema.json
  contracts/failure-bundle.schema.json
  contracts/cli-envelope.schema.json
  contracts/knowledge-experience.schema.json
  contracts/memory-context.schema.json
  contracts/run-event.schema.json
  contracts/run-policy.schema.json
  contracts/agent-action.schema.json
  contracts/browser-action.schema.json
  contracts/user-story-contract.schema.json
  docs/adr/0009-run-workflow-shape-and-retry-ownership.md
  templates/MEMORY_EVAL_TEMPLATE.md
)

for f in "${required[@]}"; do
  test -f "$f" || { echo "missing: $f" >&2; exit 1; }
done

# The property worth guarding is contiguity, not a total: a plan numbered 19 beside a
# missing 18 means a phase was skipped or deleted, while a hardcoded count has to be
# edited on every phase — and a check that taxes the work it guards gets deleted.
phase_files="$(find plans -maxdepth 1 -type f -name 'phase-[0-9][0-9]-*.md' | sort)"
phase_numbers="$(printf '%s\n' "$phase_files" | sed -E 's|.*/phase-([0-9][0-9])-.*|\1|')"
phase_count="$(printf '%s\n' "$phase_numbers" | grep -c '[0-9]')"

test "$phase_count" -ge 15 || {
  echo "expected at least the 15 closed phases, found $phase_count" >&2
  exit 1
}

expected="$(seq -w 0 "$((phase_count - 1))")"
test "$phase_numbers" = "$expected" || {
  echo "phase plans are not contiguous from 00" >&2
  echo "found:    $(printf '%s ' $phase_numbers)" >&2
  echo "expected: $(printf '%s ' $expected)" >&2
  exit 1
}

for schema in contracts/*.schema.json; do
  python -m json.tool "$schema" >/dev/null
done

skill_count="$(find .claude/skills -mindepth 2 -maxdepth 2 -type f -name SKILL.md | wc -l | tr -d ' ')"
test "$skill_count" = "20" || { echo "expected 20 project skills, found $skill_count" >&2; exit 1; }

grep -q "falkordb_data" infra/compose/compose.blueprint.yaml || { echo "FalkorDB persistence volume missing" >&2; exit 1; }
grep -q "adaptive-memory-graph" plans/phase-09-knowledge-memory.md || { echo "Phase 09 memory skill routing missing" >&2; exit 1; }

echo "blueprint ok: 15 phases, 20 skills, adaptive memory contracts valid"
