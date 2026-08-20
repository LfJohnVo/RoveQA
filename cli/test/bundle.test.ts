/**
 * FailureBundle integrity and atomic materialization.
 *
 * Three properties, all of which fail silently if nobody checks them: a bundle never
 * mixes evidence from two runs, its files are the files its manifest describes, and a
 * bundle directory is never quietly partial.
 */

import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { CliError } from "../src/errors.js";
import {
  MANIFEST_NAME,
  PARTIAL_MARKER,
  assertBytesMatch,
  assertCoherent,
  materialize,
  safeJoin,
  type BundleArtifact,
  type BundleManifest,
} from "../src/bundle/materialize.js";

const SCREENSHOT = Buffer.from("not really a png");
// The real digest of the bytes above. It used to be a placeholder, which nothing
// noticed because nothing compared it to anything.
const SHA_OF_SCREENSHOT = createHash("sha256").update(SCREENSHOT).digest("hex");

function artifact(overrides: Partial<BundleArtifact> = {}): BundleArtifact {
  return {
    artifact_id: "art-1",
    kind: "screenshot",
    relative_path: "screenshots/final.png",
    sha256: SHA_OF_SCREENSHOT,
    size_bytes: SCREENSHOT.length,
    run_id: "run-1",
    evidence_set_id: "evidence-1",
    ...overrides,
  };
}

function manifest(overrides: Partial<BundleManifest> = {}): BundleManifest {
  return {
    schema_version: "roveqa.failure-bundle.v1",
    bundle_id: "bundle:run-1",
    run_id: "run-1",
    evidence_set_id: "evidence-1",
    project_id: "project-1",
    plan_version: "1",
    verdict: "failed",
    captured_at: "2026-08-19T00:00:00Z",
    deterministic_observation: "the page does not contain 'Order #'",
    root_cause_hypothesis: null,
    artifacts: [artifact()],
    ...overrides,
  };
}

function workspace(): string {
  return mkdtempSync(join(tmpdir(), "roveqa-bundle-"));
}

const fetchOk = () => Promise.resolve(SCREENSHOT);

describe("provenance", () => {
  it("refuses an artifact from another run", async () => {
    // The failure this prevents: a bundle that reads as coherent and is not.
    const contaminated = manifest({ artifacts: [artifact({ run_id: "run-2" })] });

    expect(() => assertCoherent(contaminated)).toThrow(/belongs to run run-2/);
    await expect(materialize(contaminated, join(workspace(), "b"), fetchOk)).rejects.toThrow(
      CliError,
    );
  });

  it("refuses an artifact from another evidence set", () => {
    const contaminated = manifest({
      artifacts: [artifact(), artifact({ artifact_id: "art-2", evidence_set_id: "evidence-2" })],
    });

    expect(() => assertCoherent(contaminated)).toThrow(/evidence set/);
  });

  it("refuses a manifest that does not satisfy the published schema", () => {
    const broken = manifest();
    delete (broken as Record<string, unknown>).evidence_set_id;

    expect(() => assertCoherent(broken)).toThrow(/invalid failure manifest/);
  });

  it("accepts a coherent manifest", () => {
    expect(() => assertCoherent(manifest())).not.toThrow();
  });
});

describe("integrity", () => {
  it("refuses bytes that do not hash to what the manifest declares", async () => {
    // A hash nobody compares is decoration. The bundle is what a reader trusts
    // afterwards, so a body that was truncated or rewritten in flight must not reach
    // the disk under a manifest that says otherwise.
    const destination = join(workspace(), "failure");

    await expect(
      materialize(manifest(), destination, () => Promise.resolve(Buffer.from("tampered bytes!!"))),
    ).rejects.toThrow(/hashes to/);

    expect(existsSync(destination)).toBe(false);
    expect(existsSync(join(`${destination}.staging`, PARTIAL_MARKER))).toBe(true);
  });

  it("refuses a truncated download before hashing it", () => {
    expect(() => assertBytesMatch(artifact(), SCREENSHOT.subarray(0, 4))).toThrow(
      /downloaded as 4 bytes/,
    );
  });

  it("accepts the bytes the manifest describes", () => {
    expect(() => assertBytesMatch(artifact(), SCREENSHOT)).not.toThrow();
  });
});

describe("path safety", () => {
  it.each([
    "../escape.png",
    "/etc/passwd",
    "C:\\Windows\\system32",
    "screenshots\\final.png",
    "nested/../../escape.png",
  ])("refuses %s", (path) => {
    expect(() => safeJoin("/bundle", path)).toThrow(CliError);
  });

  it("accepts a path that stays inside", () => {
    expect(safeJoin("/bundle", "screenshots/final.png")).toContain("screenshots");
  });

  it("refuses an escaping path even when the schema let it through", async () => {
    // Belt and braces: the schema's pattern and this check protect the same thing,
    // and the one that runs against the resolved path is the one that counts.
    const evil = manifest({ artifacts: [artifact({ relative_path: "ok.png" })] });
    evil.artifacts[0]!.relative_path = "../escaped.png";

    await expect(materialize(evil, join(workspace(), "b"), fetchOk)).rejects.toThrow(CliError);
  });
});

describe("atomic materialization", () => {
  it("writes the manifest last and leaves no marker behind", async () => {
    const destination = join(workspace(), "failure");

    const result = await materialize(manifest(), destination, fetchOk);

    expect(existsSync(result.manifestPath)).toBe(true);
    expect(existsSync(join(destination, PARTIAL_MARKER))).toBe(false);
    expect(existsSync(join(destination, "screenshots", "final.png"))).toBe(true);
    expect(existsSync(join(destination, "observation.json"))).toBe(true);
  });

  it("leaves a .partial marker and no destination when an artifact cannot be fetched", async () => {
    const destination = join(workspace(), "failure");

    await expect(
      materialize(manifest(), destination, () => Promise.reject(new Error("network died"))),
    ).rejects.toThrow(CliError);

    // Nothing consumable was produced, and the wreckage is marked as wreckage.
    expect(existsSync(destination)).toBe(false);
    expect(existsSync(join(`${destination}.staging`, PARTIAL_MARKER))).toBe(true);
    expect(existsSync(join(`${destination}.staging`, MANIFEST_NAME))).toBe(false);
  });

  it("does not destroy an existing bundle when the new one fails", async () => {
    // The old bundle is somebody's evidence. A failed refresh must not take it away.
    const destination = join(workspace(), "failure");
    await materialize(manifest(), destination, fetchOk);
    const before = readFileSync(join(destination, MANIFEST_NAME), "utf8");

    await expect(
      materialize(manifest(), destination, () => Promise.reject(new Error("network died"))),
    ).rejects.toThrow(CliError);

    expect(readFileSync(join(destination, MANIFEST_NAME), "utf8")).toBe(before);
  });

  it("replaces a leftover staging directory instead of merging into it", async () => {
    const destination = join(workspace(), "failure");
    const staging = `${destination}.staging`;
    writeFileSync(join(workspace(), "unused"), "");
    await materialize(manifest(), destination, fetchOk);

    // A second run must not inherit a file from an abandoned first attempt.
    expect(existsSync(staging)).toBe(false);
  });

  it("writes the hypothesis only when a model produced one", async () => {
    const destination = join(workspace(), "failure");

    await materialize(manifest(), destination, fetchOk);
    expect(existsSync(join(destination, "hypothesis.json"))).toBe(false);

    const withGuess = manifest({
      root_cause_hypothesis: { text: "probably the cart", model_derived: true },
    });
    const second = join(workspace(), "failure2");
    await materialize(withGuess, second, fetchOk);

    const written: unknown = JSON.parse(readFileSync(join(second, "hypothesis.json"), "utf8"));
    expect((written as { model_derived: boolean }).model_derived).toBe(true);
  });

  it("round-trips the manifest through its schema", async () => {
    const destination = join(workspace(), "failure");
    await materialize(manifest(), destination, fetchOk);

    const written: unknown = JSON.parse(readFileSync(join(destination, MANIFEST_NAME), "utf8"));

    expect(() => assertCoherent(written as BundleManifest)).not.toThrow();
  });
});
