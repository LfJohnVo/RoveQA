/**
 * `roveqa agent install claude` — install the verification skill into a repository.
 *
 * The rule that governs every write here: **never clobber instructions somebody else
 * wrote.** The skill goes into its own file under a managed directory, and the one
 * shared file it touches (`CLAUDE.md`) is edited only between explicit markers, so a
 * second install replaces the block it owns and leaves every other line alone.
 *
 * A tool that rewrote a project's agent instructions to install itself would be
 * uninstallable in practice: nobody could tell what it had taken out.
 */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import { CliError } from "../errors.js";

export const SKILL_PATH = join(".claude", "skills", "roveqa-verify", "SKILL.md");
export const BEGIN_MARKER = "<!-- roveqa:begin -->";
export const END_MARKER = "<!-- roveqa:end -->";

export interface InstallInput {
  cwd: string;
  /** Written into the skill so the agent runs against this project by default. */
  projectId?: string | undefined;
  apiUrl?: string | undefined;
  force?: boolean;
}

export interface InstallResult {
  skill_path: string;
  instructions_path: string;
  skill_written: boolean;
  instructions_updated: boolean;
}

export const SUPPORTED_AGENTS = ["claude"] as const;
export type SupportedAgent = (typeof SUPPORTED_AGENTS)[number];

export function requireSupportedAgent(name: string | undefined): SupportedAgent {
  if (name === undefined || !(SUPPORTED_AGENTS as readonly string[]).includes(name)) {
    throw new CliError("USAGE_ERROR", `unknown agent: ${name ?? "(none)"}`, {
      nextAction: `Supported: ${SUPPORTED_AGENTS.join(", ")}`,
    });
  }
  return name as SupportedAgent;
}

export async function installClaudeSkill(input: InstallInput): Promise<InstallResult> {
  const skillPath = join(input.cwd, SKILL_PATH);
  const instructionsPath = join(input.cwd, "CLAUDE.md");

  const existingSkill = await readIfPresent(skillPath);
  if (existingSkill !== null && input.force !== true && !existingSkill.includes(BEGIN_MARKER)) {
    // Someone hand-wrote a skill at this path. Overwriting it would destroy work
    // this tool has no way to reconstruct.
    throw new CliError("CONFLICT", `${skillPath} exists and was not written by roveqa`, {
      nextAction: "Move it aside, or pass --force to replace it.",
    });
  }

  await mkdir(dirname(skillPath), { recursive: true });
  await writeFile(skillPath, skillDocument(input));

  const instructionsUpdated = await updateInstructions(instructionsPath);
  return {
    skill_path: skillPath,
    instructions_path: instructionsPath,
    skill_written: true,
    instructions_updated: instructionsUpdated,
  };
}

/**
 * Add or replace only the block between the markers.
 *
 * A file that has no markers gets the block appended; one that has them keeps
 * everything outside them untouched. That is what makes reinstalling safe.
 */
async function updateInstructions(path: string): Promise<boolean> {
  const block = [
    BEGIN_MARKER,
    "",
    "## Verifying with RoveQA",
    "",
    "After completing a feature or fix, verify it with a real run before claiming it works:",
    "",
    "```bash",
    "roveqa plan lint <plan.json>",
    "roveqa run create --plan <plan.json> --output json",
    "roveqa run wait <run-id> --output json",
    "```",
    "",
    "Exit `0` means the run passed. Exit `1` is a terminal non-pass verdict — read it,",
    "do not retry it. Exit `7` means the wait timed out and the run is **still going**:",
    "that is not a failure and must not be reported as one.",
    "",
    "On a non-pass verdict, collect the evidence before drawing a conclusion:",
    "",
    "```bash",
    "roveqa run failure <run-id> --out ./failure --output json",
    "```",
    "",
    "`deterministic_observation` is what was actually observed. `root_cause_hypothesis`",
    "is a model's guess and is labelled as one; never present it as a finding.",
    "",
    "Never claim something is verified without a terminal verdict from a real run.",
    "",
    END_MARKER,
  ].join("\n");

  const existing = await readIfPresent(path);
  if (existing === null) {
    await writeFile(path, `${block}\n`);
    return true;
  }

  const begin = existing.indexOf(BEGIN_MARKER);
  const end = existing.indexOf(END_MARKER);
  if (begin !== -1 && end !== -1 && end > begin) {
    const replaced =
      existing.slice(0, begin) + block + existing.slice(end + END_MARKER.length);
    if (replaced === existing) return false;
    await writeFile(path, replaced);
    return true;
  }

  // No markers: append rather than rewrite, so nothing already in the file moves.
  await writeFile(path, `${existing.replace(/\n*$/, "")}\n\n${block}\n`);
  return true;
}

function skillDocument(input: InstallInput): string {
  const context = [
    input.projectId === undefined ? null : `- Project: \`${input.projectId}\``,
    input.apiUrl === undefined ? null : `- API: \`${input.apiUrl}\``,
  ].filter((line): line is string => line !== null);

  return `${BEGIN_MARKER}
---
name: roveqa-verify
description: Verify a change by running RoveQA against the local, self-hosted platform. Use after completing a feature or fix, before claiming it works.
---

# Verifying a change with RoveQA

RoveQA runs here, on this machine. There is no hosted service and nothing leaves the
network: the CLI talks to the local FastAPI control plane, which drives a local
browser and a local model.

${context.length > 0 ? `${context.join("\n")}\n` : ""}
## The loop

1. Find an existing plan that covers the behaviour you changed. Author a minimal new
   one only if none does.
2. \`roveqa plan lint <plan.json>\` — offline; catches schema, budget and step-identity
   problems before a run is spent.
3. \`roveqa run create --plan <plan.json> --output json\`
4. \`roveqa run wait <run-id> --output json\`
5. On a non-pass verdict, \`roveqa run failure <run-id> --out ./failure --output json\`.

## Reading the result

- Exit \`0\`: the run passed.
- Exit \`1\`: a terminal non-pass verdict (\`failed\`, \`blocked\`, \`inconclusive\`,
  \`cancelled\`). Read the verdict; do not retry the command hoping for a different one.
- Exit \`7\`: the client's wait timed out. **The run is still going.** Resume with
  \`roveqa run wait <run-id>\`. Never report this as a failure.
- Any other non-zero code is the CLI or the transport, not the product.

Only \`failure_kind: product\` means there is a bug. \`plan\`, \`environment\`, \`policy\`,
\`agent_budget\` and \`model\` mean the run could not answer the question — fix the setup
or the plan, do not file a defect.

\`deterministic_observation\` can be reproduced without a model. \`root_cause_hypothesis\`
is a model's guess, labelled as one. Do not repeat a hypothesis as a finding.

## The rule

Never claim a change is verified without a terminal verdict from a real run.
A green \`plan lint\` is not a verification; it means the plan is well-formed.
${END_MARKER}
`;
}

async function readIfPresent(path: string): Promise<string | null> {
  try {
    return await readFile(path, "utf8");
  } catch {
    return null;
  }
}
