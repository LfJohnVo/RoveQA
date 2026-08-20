/**
 * The CI adapter, over the published envelope examples.
 *
 * One property matters more than the XML: the adapter never decides the outcome. It
 * exits with the code the CLI gave it. An adapter that reported "tests ran" while the
 * run had timed out would make a green pipeline out of a question nobody answered.
 */

import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
// Shipped with the package: an external consumer installs the CLI and gets the adapter,
// rather than being told to copy a file out of a repository they do not have.
const adapter = join(packageRoot, "examples", "verdict-to-junit.mjs");
const examples = join(packageRoot, "contracts", "examples");

function convert(example: string, exitCode: number): { xml: string; code: number } {
  try {
    const xml = execFileSync(
      process.execPath,
      [adapter, join(examples, example), String(exitCode)],
      { encoding: "utf8" },
    );
    return { xml, code: 0 };
  } catch (error) {
    const failure = error as { status?: number; stdout?: string };
    return { xml: failure.stdout ?? "", code: failure.status ?? -1 };
  }
}

describe("translating a verdict for CI", () => {
  it("passes the CLI's exit code straight through", () => {
    // 1 is a terminal non-pass. The adapter reports it; it does not reinterpret it.
    const { code } = convert("cli-envelope.success.example.json", 1);

    expect(code).toBe(1);
  });

  it("does not turn a wait timeout into a failure or a pass", () => {
    // The run is still going. Calling it failed would be as wrong as calling it passed.
    const { xml, code } = convert("cli-envelope.error.example.json", 7);

    expect(code).toBe(7);
    expect(xml).toMatch(/errors="1"/);
    expect(xml).toMatch(/WAIT_TIMEOUT/);
    expect(xml).not.toMatch(/<failure/);
  });

  it("records a non-pass verdict as a failure with its name", () => {
    const { xml } = convert("cli-envelope.success.example.json", 1);

    expect(xml).toMatch(/failures="1"/);
    expect(xml).toMatch(/verdict: failed/);
  });

  it("emits XML a reader can parse in every case", () => {
    for (const [example, code] of [
      ["cli-envelope.success.example.json", 1],
      ["cli-envelope.error.example.json", 7],
    ] as const) {
      const { xml } = convert(example, code);
      expect(xml.startsWith('<?xml version="1.0"')).toBe(true);
      expect(xml).toMatch(/<\/testsuite>/);
    }
  });
});
