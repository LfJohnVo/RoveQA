/**
 * `agent install claude` writes into somebody else's repository.
 *
 * Every test here is about the same promise: nothing this command writes may destroy
 * instructions a person wrote. A tool that rewrote a project's agent file to install
 * itself would be uninstallable in practice, because nobody could tell what it took
 * out.
 */

import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { describe, expect, it } from "vitest";

import { CliError } from "../src/errors.js";
import {
  BEGIN_MARKER,
  END_MARKER,
  SKILL_PATH,
  installClaudeSkill,
  requireSupportedAgent,
} from "../src/commands/agent.js";

function repository(files: Record<string, string> = {}): string {
  const cwd = mkdtempSync(join(tmpdir(), "roveqa-agent-"));
  for (const [relative, contents] of Object.entries(files)) {
    const path = join(cwd, relative);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, contents);
  }
  return cwd;
}

describe("agent selection", () => {
  it("refuses an agent it does not know", () => {
    expect(() => requireSupportedAgent("cursor")).toThrow(CliError);
    expect(() => requireSupportedAgent(undefined)).toThrow(/unknown agent/);
  });

  it("accepts claude", () => {
    expect(requireSupportedAgent("claude")).toBe("claude");
  });
});

describe("installing", () => {
  it("writes the skill into its own managed directory", async () => {
    const cwd = repository();

    const result = await installClaudeSkill({ cwd, projectId: "p-1", apiUrl: "http://api.test" });

    const skill = readFileSync(result.skill_path, "utf8");
    expect(result.skill_path).toContain(SKILL_PATH);
    expect(skill).toContain("name: roveqa-verify");
    expect(skill).toContain("p-1");
  });

  it("creates CLAUDE.md when the repository has none", async () => {
    const cwd = repository();

    const result = await installClaudeSkill({ cwd });

    const instructions = readFileSync(result.instructions_path, "utf8");
    expect(instructions).toContain(BEGIN_MARKER);
    expect(instructions).toContain(END_MARKER);
    expect(result.instructions_updated).toBe(true);
  });

  it("appends to an existing CLAUDE.md without touching what was there", async () => {
    const existing = "# House rules\n\nAlways run the linter.\n";
    const cwd = repository({ "CLAUDE.md": existing });

    await installClaudeSkill({ cwd });

    const instructions = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    expect(instructions).toContain("Always run the linter.");
    expect(instructions.indexOf("House rules")).toBeLessThan(instructions.indexOf(BEGIN_MARKER));
  });

  it("replaces only its own block when reinstalled", async () => {
    // The failure this prevents: a second install duplicating the block, or eating
    // the lines a person added after it.
    const cwd = repository({ "CLAUDE.md": "# House rules\n\nAlways run the linter.\n" });
    await installClaudeSkill({ cwd });
    const after = join(cwd, "CLAUDE.md");
    writeFileSync(after, `${readFileSync(after, "utf8")}\n## Added later\n\nBe kind.\n`);

    await installClaudeSkill({ cwd });

    const instructions = readFileSync(after, "utf8");
    expect(instructions.split(BEGIN_MARKER)).toHaveLength(2);
    expect(instructions).toContain("Always run the linter.");
    expect(instructions).toContain("Be kind.");
  });

  it("reports when a reinstall changed nothing", async () => {
    const cwd = repository();
    await installClaudeSkill({ cwd });

    const second = await installClaudeSkill({ cwd });

    expect(second.instructions_updated).toBe(false);
  });

  it("refuses to overwrite a hand-written skill at the same path", async () => {
    const cwd = repository({ [SKILL_PATH]: "# my own skill\n" });

    await expect(installClaudeSkill({ cwd })).rejects.toThrow(/was not written by roveqa/);
    expect(readFileSync(join(cwd, SKILL_PATH), "utf8")).toBe("# my own skill\n");
  });

  it("replaces a hand-written skill only when told to", async () => {
    const cwd = repository({ [SKILL_PATH]: "# my own skill\n" });

    const result = await installClaudeSkill({ cwd, force: true });

    expect(readFileSync(result.skill_path, "utf8")).toContain("roveqa-verify");
  });
});

describe("what the skill says", () => {
  it("tells the agent that a wait timeout is not a failure", async () => {
    // The most damaging misreading available: reporting exit 7 as a failing run.
    const cwd = repository();

    const result = await installClaudeSkill({ cwd });

    const skill = readFileSync(result.skill_path, "utf8");
    expect(skill).toContain("still going");
    expect(skill).toContain("Never report this as a failure");
  });

  it("tells the agent not to repeat a model hypothesis as a finding", async () => {
    const cwd = repository();

    const skill = readFileSync((await installClaudeSkill({ cwd })).skill_path, "utf8");

    expect(skill).toContain("root_cause_hypothesis");
    expect(skill).toContain("Do not repeat a hypothesis as a finding");
  });

  it("tells the agent that only a product failure is a defect", async () => {
    const cwd = repository();

    const skill = readFileSync((await installClaudeSkill({ cwd })).skill_path, "utf8");

    expect(skill).toContain("failure_kind: product");
    expect(skill).toContain("do not file a defect");
  });
});
