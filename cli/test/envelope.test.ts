/**
 * The output contract, measured on a real process.
 *
 * An agent driving this CLI has exactly two things to work with: one JSON value on
 * stdout and a numeric exit code. Everything here is about those two never lying.
 */

import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import ajv2020 from "ajv/dist/2020.js";
import type { SchemaObject } from "ajv";
import { describe, expect, it } from "vitest";

import { parseSingleJson, runCli } from "./helpers.js";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
// The published envelope schema, not a copy: this suite exists to catch the CLI
// drifting away from the contract other tools validate against.
const envelopeSchema = JSON.parse(
  readFileSync(join(packageRoot, "contracts", "cli-envelope.schema.json"), "utf8"),
) as SchemaObject;
const validateEnvelope = new ajv2020.default({ strict: false }).compile(envelopeSchema);

function workspace(): string {
  return mkdtempSync(join(tmpdir(), "roveqa-cli-"));
}

const VALID_PLAN = {
  schema_version: "roveqa.test-plan.v1",
  project_id: "project-1",
  name: "Checkout",
  mode: "story",
  run_policy_id: "policy-1",
  plan_steps: [
    { step_id: "checkout", type: "action", description: "Check out with a saved card" },
    {
      step_id: "assert-order",
      type: "assertion",
      description: "The confirmation shows an order number",
      criterion_id: "ac-1",
    },
  ],
};

describe("json output purity", () => {
  it("emits exactly one envelope on success", async () => {
    const directory = workspace();
    const path = join(directory, "plan.json");
    writeFileSync(path, JSON.stringify(VALID_PLAN));

    const result = await runCli(["plan", "lint", path, "--output", "json"], { cwd: directory });

    expect(result.code).toBe(0);
    const envelope = parseSingleJson(result.stdout);
    expect(validateEnvelope(envelope), JSON.stringify(validateEnvelope.errors)).toBe(true);
    expect(envelope.schema_version).toBe("roveqa.cli.v1");
  });

  it("emits exactly one envelope on failure", async () => {
    const result = await runCli(["plan", "lint", "/nonexistent/plan.json", "--output", "json"]);

    expect(result.code).toBe(4);
    const envelope = parseSingleJson(result.stdout);
    expect(validateEnvelope(envelope), JSON.stringify(validateEnvelope.errors)).toBe(true);
    expect((envelope.error as { code: string }).code).toBe("NOT_FOUND");
  });

  it("keeps warnings off stdout", async () => {
    // A positional step id is a real warning, so this asserts that a *diagnostic the
    // command genuinely wants to print* still cannot corrupt the payload.
    const directory = workspace();
    const path = join(directory, "plan.json");
    writeFileSync(
      path,
      JSON.stringify({
        ...VALID_PLAN,
        plan_steps: [
          { step_id: "step-1", type: "action", description: "Check out" },
          {
            step_id: "step-2",
            type: "assertion",
            description: "It worked",
            criterion_id: "ac-1",
          },
        ],
      }),
    );

    const result = await runCli(["plan", "lint", path, "--output", "json"], { cwd: directory });

    expect(result.code).toBe(0);
    expect(result.stderr).toContain("not stable");
    // The assertion that matters: stdout still parses as one value.
    const envelope = parseSingleJson(result.stdout);
    expect((envelope.data as { findings: unknown[] }).findings).toHaveLength(2);
  });

  it("refuses an unknown output mode instead of falling back to text", async () => {
    // Falling back would print human text to a caller that is parsing JSON.
    const result = await runCli(["plan", "lint", "plan.json", "--output", "yaml"]);

    expect(result.code).toBe(2);
    expect(result.stdout).toContain("USAGE_ERROR");
  });
});

describe("exit codes", () => {
  it("maps a validation failure to 5", async () => {
    const directory = workspace();
    const path = join(directory, "plan.json");
    writeFileSync(path, JSON.stringify({ schema_version: "roveqa.test-plan.v1" }));

    const result = await runCli(["plan", "lint", path, "--output", "json"], { cwd: directory });

    expect(result.code).toBe(5);
    const envelope = parseSingleJson(result.stdout);
    expect((envelope.error as { code: string }).code).toBe("VALIDATION_ERROR");
    // The error carries what to fix, so an agent does not have to guess.
    expect((envelope.error as { details: { findings: unknown[] } }).details.findings.length)
      .toBeGreaterThan(0);
  });

  it("maps an unknown command to 2", async () => {
    const result = await runCli(["plan", "teleport", "--output", "json"]);

    expect(result.code).toBe(2);
    expect((parseSingleJson(result.stdout).error as { code: string }).code).toBe("USAGE_ERROR");
  });
});

describe("plan scaffold", () => {
  it("produces a plan its own linter accepts", async () => {
    // scaffold -> lint is the first loop an author runs; if it does not hold, the
    // starting point of every plan is already broken.
    const directory = workspace();
    const scaffold = await runCli(
      ["plan", "scaffold", "--project", "project-1", "--policy-id", "policy-1"],
      { cwd: directory },
    );
    expect(scaffold.code).toBe(0);

    const path = join(directory, "plan.json");
    writeFileSync(path, scaffold.stdout);
    const lint = await runCli(["plan", "lint", path, "--output", "json"], { cwd: directory });

    expect(lint.code).toBe(0);
    expect((parseSingleJson(lint.stdout).data as { valid: boolean }).valid).toBe(true);
  });

  it("needs a project id and says how to supply one", async () => {
    const result = await runCli(["plan", "scaffold", "--output", "json"], { cwd: workspace() });

    expect(result.code).toBe(2);
    const envelope = parseSingleJson(result.stdout);
    expect((envelope.error as { next_action: string }).next_action).toContain("ROVEQA_PROJECT_ID");
  });

  it("takes the project id from the environment", async () => {
    const directory = workspace();
    const result = await runCli(["plan", "scaffold", "--output", "json"], {
      cwd: directory,
      env: { ROVEQA_PROJECT_ID: "from-env", ROVEQA_HOME: directory },
    });

    expect(result.code).toBe(0);
    expect((parseSingleJson(result.stdout).data as { project_id: string }).project_id).toBe(
      "from-env",
    );
  });
});
