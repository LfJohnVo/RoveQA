/**
 * Materialize a FailureBundle on disk.
 *
 * The rule the whole module serves: **a bundle directory is either complete or
 * visibly incomplete, never quietly partial**. A consumer that finds `manifest.json`
 * must be able to trust everything it references is there.
 *
 * That is why files are written into a sibling temporary directory first, the whole
 * directory is promoted in one rename, and `manifest.json` is written last inside it.
 * A crash leaves the temporary directory behind with a `.partial` marker and the
 * destination untouched.
 *
 * The second rule is provenance: every artifact must name the same `run_id` and
 * `evidence_set_id` as the manifest. Mixing "the latest screenshot" with another
 * run's console log produces a bundle that looks coherent and is not, which is worse
 * than having no bundle at all.
 */

import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, join, normalize, relative, resolve, sep } from "node:path";

import { CliError } from "../errors.js";
import { validateAgainst } from "../contracts/schemas.js";

export const PARTIAL_MARKER = ".partial";
export const MANIFEST_NAME = "manifest.json";

export interface BundleArtifact {
  artifact_id: string;
  kind: string;
  relative_path: string;
  sha256: string;
  size_bytes: number;
  run_id: string;
  evidence_set_id: string;
}

export interface BundleManifest {
  schema_version: string;
  bundle_id: string;
  run_id: string;
  evidence_set_id: string;
  project_id: string;
  plan_version: string;
  verdict: string;
  captured_at: string;
  artifacts: BundleArtifact[];
  deterministic_observation?: string | null;
  root_cause_hypothesis?: { text: string; model_derived: true } | null;
  [key: string]: unknown;
}

export interface MaterializeResult {
  directory: string;
  manifestPath: string;
  artifactCount: number;
}

/**
 * Check that everything in the manifest belongs to the same failure.
 *
 * Run before a single byte is written, because a contaminated bundle that already
 * exists on disk is one somebody may already have read.
 */
export function assertCoherent(manifest: BundleManifest): void {
  const problems = validateAgainst("failure-bundle", manifest);
  if (problems.length > 0) {
    throw new CliError("VALIDATION_ERROR", "the server returned an invalid failure manifest", {
      details: { problems },
    });
  }

  for (const artifact of manifest.artifacts) {
    if (artifact.run_id !== manifest.run_id) {
      throw new CliError(
        "VALIDATION_ERROR",
        `artifact ${artifact.artifact_id} belongs to run ${artifact.run_id}, ` +
          `not ${manifest.run_id}`,
        { nextAction: "Refusing to write a bundle that mixes evidence from two runs." },
      );
    }
    if (artifact.evidence_set_id !== manifest.evidence_set_id) {
      throw new CliError(
        "VALIDATION_ERROR",
        `artifact ${artifact.artifact_id} belongs to evidence set ` +
          `${artifact.evidence_set_id}, not ${manifest.evidence_set_id}`,
      );
    }
  }
}

/**
 * Resolve an artifact's path inside the bundle, refusing anything that escapes.
 *
 * The schema already forbids `..` and absolute paths, but a path from a server is
 * still input: the resolved location is checked to stay under the bundle root, which
 * is the check that actually prevents a write outside it.
 */
export function safeJoin(root: string, relativePath: string): string {
  if (isAbsolute(relativePath) || /^[A-Za-z]:/.test(relativePath) || relativePath.includes("\\")) {
    throw new CliError("VALIDATION_ERROR", `unsafe artifact path: ${relativePath}`);
  }
  const target = resolve(root, normalize(relativePath));
  const inside = relative(resolve(root), target);
  if (inside === "" || inside.startsWith("..") || isAbsolute(inside)) {
    throw new CliError("VALIDATION_ERROR", `artifact path escapes the bundle: ${relativePath}`);
  }
  return target;
}

export interface ArtifactFetcher {
  (artifact: BundleArtifact): Promise<Buffer>;
}

/**
 * Write the bundle atomically.
 *
 * `fetch` is injected because downloading artifacts is the API's business and
 * assembling a coherent directory is this module's; keeping them apart is what lets
 * the atomicity be tested without a server.
 */
export async function materialize(
  manifest: BundleManifest,
  destination: string,
  fetch: ArtifactFetcher,
): Promise<MaterializeResult> {
  assertCoherent(manifest);

  const staging = `${destination}.staging`;
  await rm(staging, { recursive: true, force: true });
  await mkdir(staging, { recursive: true });
  // Present from the first byte: anything that finds this directory mid-write knows
  // not to read it. It is removed only when the bundle is complete.
  await writeFile(join(staging, PARTIAL_MARKER), "materializing\n");

  try {
    for (const artifact of manifest.artifacts) {
      const target = safeJoin(staging, artifact.relative_path);
      await mkdir(dirname(target), { recursive: true });
      await writeFile(target, await fetch(artifact));
    }

    // Projections of the manifest, for readers who want one field without parsing
    // the whole thing. The manifest stays authoritative on any divergence (docs/25).
    await writeFile(
      join(staging, "observation.json"),
      `${JSON.stringify({ deterministic_observation: manifest.deterministic_observation ?? null }, null, 2)}\n`,
    );
    if (manifest.root_cause_hypothesis) {
      await writeFile(
        join(staging, "hypothesis.json"),
        `${JSON.stringify(manifest.root_cause_hypothesis, null, 2)}\n`,
      );
    }

    // Manifest last, marker gone last of all: their order is the completion signal.
    await writeFile(join(staging, MANIFEST_NAME), `${JSON.stringify(manifest, null, 2)}\n`);
    await rm(join(staging, PARTIAL_MARKER));

    await rm(destination, { recursive: true, force: true });
    await mkdir(dirname(destination), { recursive: true });
    await rename(staging, destination);
  } catch (error) {
    // The staging directory is left in place, marker and all: it is evidence of what
    // went wrong, and deleting it would hide a half-downloaded artifact set.
    throw error instanceof CliError
      ? error
      : new CliError("INTERNAL_ERROR", `failed to materialize the bundle: ${describe(error)}`, {
          nextAction: `Inspect ${staging}${sep}${PARTIAL_MARKER} and retry.`,
        });
  }

  return {
    directory: destination,
    manifestPath: join(destination, MANIFEST_NAME),
    artifactCount: manifest.artifacts.length,
  };
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
