/**
 * Validating a document against one of the published contracts.
 *
 * The schemas are not checked into this package: `scripts/bundle-contracts.mjs` copies
 * them from the repository's `contracts/` directory at build time, so what the CLI
 * validates against is the same file the backend validates against. A copy living here
 * would be free to drift, and the first symptom would be a plan that lints clean in the
 * terminal and is rejected by the API.
 *
 * This module was missing from version control: `cli/.gitignore` carried an unanchored
 * `contracts/` pattern, which matched this directory as well as the copied schemas it
 * meant to ignore. Everything here therefore worked only on a machine where the file
 * already existed, and a fresh clone could not lint, type-check, build or test the CLI.
 * The pattern is anchored now.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import ajv2020 from "ajv/dist/2020.js";
import type { ErrorObject, SchemaObject, ValidateFunction } from "ajv";

/** A contract, named the way its schema file is. */
export type ContractName = "test-plan" | "cli-envelope" | "failure-bundle";

/** One reason a document does not satisfy its schema. */
export interface SchemaProblem {
  /** Where the problem is, as a JSON pointer — `/plan_steps/2/criterion_id`. */
  path: string;
  message: string;
}

const packageRoot = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const contractsDir = join(packageRoot, "contracts");

/**
 * Compiled validators, kept per contract.
 *
 * `plan lint` validates once, but `run failure` checks a manifest and then every
 * artifact it names, and recompiling a schema per byte-range would make the check cost
 * more than the download.
 */
const compiled = new Map<ContractName, ValidateFunction>();

function validatorFor(name: ContractName): ValidateFunction {
  const cached = compiled.get(name);
  if (cached !== undefined) {
    return cached;
  }

  const file = join(contractsDir, `${name}.schema.json`);
  const schema = JSON.parse(readFileSync(file, "utf8")) as SchemaObject;
  // `strict: false` for the same reason the contract-example test uses it: the published
  // schemas carry annotations Ajv's strict mode rejects, and refusing to load a schema
  // the backend accepts would make the CLI disagree with the server about what is valid.
  const validate = new ajv2020.default({ strict: false, allErrors: true }).compile(schema);
  compiled.set(name, validate);
  return validate;
}

function describe(error: ErrorObject): SchemaProblem {
  // `instancePath` is empty for a problem with the document as a whole; reporting that
  // as "" reads like a missing field, so it is named.
  const path = error.instancePath === "" ? "(document)" : error.instancePath;
  const detail =
    error.keyword === "additionalProperties" &&
    typeof error.params.additionalProperty === "string"
      ? `${error.message ?? "is invalid"}: ${error.params.additionalProperty}`
      : (error.message ?? "is invalid");
  return { path, message: detail };
}

/**
 * Every way `value` fails to satisfy `name`, or an empty list.
 *
 * A list rather than a thrown error, and every problem rather than the first: somebody
 * fixing a hand-written plan wants to see all of it, and a lint that reports one problem
 * per run is a lint people stop running.
 */
export function validateAgainst(name: ContractName, value: unknown): SchemaProblem[] {
  const validate = validatorFor(name);
  if (validate(value)) {
    return [];
  }
  return (validate.errors ?? []).map(describe);
}
