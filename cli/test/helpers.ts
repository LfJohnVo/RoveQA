/**
 * Spawn the built CLI as a real process.
 *
 * Contract tests must run the binary, not call `run()` in-process: stdout purity,
 * exit codes and stream separation are properties of the *process*, and an
 * import-level test would pass while the shipped binary printed a warning onto
 * stdout.
 */

import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
export const CLI_ENTRY = join(packageRoot, "dist", "main.js");

export interface CliResult {
  code: number;
  stdout: string;
  stderr: string;
}

export function runCli(
  args: string[],
  options: { env?: Record<string, string>; cwd?: string } = {},
): Promise<CliResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [CLI_ENTRY, ...args], {
      cwd: options.cwd ?? packageRoot,
      env: {
        PATH: process.env.PATH ?? "",
        // A stray user or project config on the machine running the suite would
        // change what these tests measure, so each one starts from nothing.
        ROVEQA_HOME: options.cwd ?? packageRoot,
        ...options.env,
      },
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk: Buffer) => (stderr += chunk.toString()));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? -1, stdout, stderr }));
  });
}

/** Parse stdout as exactly one JSON value, failing loudly when it is not. */
export function parseSingleJson(stdout: string): Record<string, unknown> {
  const trimmed = stdout.trim();
  if (trimmed === "") throw new Error("stdout was empty; expected one JSON value");
  const parsed: unknown = JSON.parse(trimmed);
  if (parsed === null || typeof parsed !== "object") {
    throw new Error(`stdout was not a JSON object: ${trimmed.slice(0, 200)}`);
  }
  return parsed as Record<string, unknown>;
}
