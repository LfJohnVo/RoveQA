/**
 * The published examples, validated against the published schemas.
 *
 * `contracts/examples/` exists so a consumer outside this repository has something to
 * compare against without reading anybody's code. An example that stopped satisfying its
 * own schema is worse than no example, because somebody would copy it — so every one is
 * validated here, against the same schema files the backend and the CLI use.
 *
 * This is also where an incompatible contract change becomes visible: adding a required
 * field breaks these fixtures, which is the point. A consumer would have broken too.
 */

import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import ajv2020 from "ajv/dist/2020.js";
import type { SchemaObject } from "ajv";
import { describe, expect, it } from "vitest";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const contracts = join(packageRoot, "contracts");
const examples = join(contracts, "examples");

function load(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

function validator(schemaFile: string) {
  const schema = load(join(contracts, schemaFile)) as SchemaObject;
  return new ajv2020.default({ strict: false }).compile(schema);
}

const PAIRS: ReadonlyArray<[example: string, schema: string]> = [
  ["test-plan.example.json", "test-plan.schema.json"],
  ["cli-envelope.success.example.json", "cli-envelope.schema.json"],
  ["cli-envelope.error.example.json", "cli-envelope.schema.json"],
  ["failure-bundle.manifest.example.json", "failure-bundle.schema.json"],
];

describe("the published examples", () => {
  it.each(PAIRS)("%s satisfies %s", (example, schema) => {
    const validate = validator(schema);

    const valid = validate(load(join(examples, example)));

    expect(validate.errors ?? []).toEqual([]);
    expect(valid).toBe(true);
  });

  it("covers every example in the directory", () => {
    // A fixture nobody validates is a fixture that will drift. Adding one to the
    // directory without adding it above fails here rather than months later.
    const present = readdirSync(examples).filter((name) => name.endsWith(".json")).sort();
    const covered = PAIRS.map(([example]) => example).sort();

    expect(present).toEqual(covered);
  });

  it("uses identifiers nobody could mistake for real ones", () => {
    // A published example carrying a real run id invites somebody to paste it into a
    // command and wonder why it does nothing.
    for (const [example] of PAIRS) {
      const raw = readFileSync(join(examples, example), "utf8");
      const ids = raw.match(/"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-z]{12}"/g) ?? [];
      for (const id of ids) {
        expect(id).toMatch(/^"00000000-0000-4000-8000-/);
      }
    }
  });
});
