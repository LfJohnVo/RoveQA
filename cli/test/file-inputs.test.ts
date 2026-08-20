/**
 * Reading a file the caller named.
 *
 * A plan file is the one input an agent hands this CLI wholesale, so it is the one
 * place where "large" is somebody else's decision. The bound has to be asked of the
 * filesystem *before* the bytes are in memory — checking the length of a string you
 * already loaded is not a bound, it is a report.
 *
 * The other two cases are about saying what went wrong. A missing file and a directory
 * both fail; failing with an errno nobody can act on is how a machine-facing tool
 * becomes one somebody has to babysit.
 */

import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { CliError } from "../src/errors.js";
import { MAX_PLAN_BYTES, readPlanFile } from "../src/commands/plan.js";

function workspace(): string {
  return mkdtempSync(join(tmpdir(), "roveqa-files-"));
}

describe("reading a plan file", () => {
  it("reads one that is fine", () => {
    const directory = workspace();
    const path = join(directory, "plan.json");
    writeFileSync(path, JSON.stringify({ schema_version: "roveqa.test-plan.v1" }));

    expect(readPlanFile(path)).toEqual({ schema_version: "roveqa.test-plan.v1" });
  });

  it("refuses a file larger than the limit without loading it", () => {
    // Written just over the cap. The point is not that it is rejected — it is that
    // the rejection does not require the file to be in memory first.
    const directory = workspace();
    const path = join(directory, "huge.json");
    writeFileSync(path, "x".repeat(MAX_PLAN_BYTES + 1));

    expect(() => readPlanFile(path)).toThrowError(
      new RegExp(`exceeds ${MAX_PLAN_BYTES} bytes`),
    );
  });

  it("accepts a file right at the limit", () => {
    // A bound, not an off-by-one that rejects a legal plan.
    const directory = workspace();
    const path = join(directory, "big.json");
    const padding = "y".repeat(MAX_PLAN_BYTES - 20);
    writeFileSync(path, JSON.stringify({ note: padding }));

    expect(() => readPlanFile(path)).not.toThrow();
  });

  it("says a directory is a directory", () => {
    const directory = workspace();
    const path = join(directory, "not-a-file");
    mkdirSync(path);

    try {
      readPlanFile(path);
      throw new Error("expected readPlanFile to throw");
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      expect((error as CliError).code).toBe("VALIDATION_ERROR");
      expect((error as CliError).message).toMatch(/is a directory/);
    }
  });

  it("says a missing file is missing", () => {
    try {
      readPlanFile(join(workspace(), "nope.json"));
      throw new Error("expected readPlanFile to throw");
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      expect((error as CliError).code).toBe("NOT_FOUND");
    }
  });

  it("says invalid JSON is invalid JSON", () => {
    const directory = workspace();
    const path = join(directory, "broken.json");
    writeFileSync(path, "{ not json");

    try {
      readPlanFile(path);
      throw new Error("expected readPlanFile to throw");
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      expect((error as CliError).code).toBe("VALIDATION_ERROR");
      expect((error as CliError).message).toMatch(/not valid JSON/);
    }
  });
});
