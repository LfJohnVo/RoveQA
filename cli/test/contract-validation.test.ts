/**
 * `validateAgainst`, exercised rather than merely compiled.
 *
 * The module it tests was absent from version control — an unanchored `contracts/` in
 * `cli/.gitignore` matched it as well as the build-time schema copy it meant to ignore —
 * so the CLI could not be built from a fresh clone. Restoring it was not enough: nothing
 * called it. `plan lint` and the bundle check both depend on it, and both would have
 * failed at runtime while lint, typecheck and build stayed green.
 *
 * A module nobody runs is a module nobody can claim works.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { validateAgainst } from "../src/contracts/schemas.js";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const examples = join(packageRoot, "contracts", "examples");

function example(name: string): unknown {
  return JSON.parse(readFileSync(join(examples, name), "utf8"));
}

describe("validating against a published contract", () => {
  it("accepts the canonical example", () => {
    // The same fixture a consumer outside this repository is told to compare against.
    expect(validateAgainst("test-plan", example("test-plan.example.json"))).toEqual([]);
  });

  it("accepts a canonical failure manifest", () => {
    const problems = validateAgainst(
      "failure-bundle",
      example("failure-bundle.manifest.example.json"),
    );

    expect(problems).toEqual([]);
  });

  it("reports a missing required field with a path somebody can act on", () => {
    // `schema_version` is required by the schema; `plan_id` is not, which is worth
    // knowing — a lint cannot report a field the contract does not insist on.
    const plan = example("test-plan.example.json") as Record<string, unknown>;
    delete plan.schema_version;

    const problems = validateAgainst("test-plan", plan);

    expect(problems.length).toBeGreaterThan(0);
    expect(problems.some((problem) => problem.message.includes("schema_version"))).toBe(true);
  });

  it("names the document rather than an empty path for a whole-document problem", () => {
    // An empty `path` reads like a missing field name, which sends the reader looking in
    // the wrong place.
    const problems = validateAgainst("test-plan", "not an object at all");

    expect(problems.length).toBeGreaterThan(0);
    expect(problems[0]?.path).toBe("(document)");
  });

  it("reports every problem, not only the first", () => {
    // Somebody fixing a hand-written plan wants to see all of it; a lint that reports one
    // problem per run is a lint people stop running.
    const problems = validateAgainst("test-plan", {});

    expect(problems.length).toBeGreaterThan(1);
  });

  it("points at the offending element inside a nested array", () => {
    const plan = example("test-plan.example.json") as { plan_steps: Record<string, unknown>[] };
    // A step missing `type` and `description`, both required of every item.
    plan.plan_steps[0] = { step_id: "broken" };

    const problems = validateAgainst("test-plan", plan);

    expect(problems.some((problem) => problem.path.startsWith("/plan_steps/0"))).toBe(true);
  });

  it("compiles a schema once and reuses it", () => {
    // `run failure` checks a manifest and then every artifact it names; recompiling per
    // call would make the check cost more than the download.
    const first = validateAgainst("test-plan", example("test-plan.example.json"));
    const second = validateAgainst("test-plan", example("test-plan.example.json"));

    expect(first).toEqual([]);
    expect(second).toEqual([]);
  });
});
