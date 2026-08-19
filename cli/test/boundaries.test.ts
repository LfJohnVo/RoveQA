/**
 * The CLI is a delivery adapter. It talks to the HTTP API and to nothing else.
 *
 * This is a test rather than a review habit because the failure it prevents is easy
 * to introduce and invisible afterwards: one `pg` import to "just check the run
 * directly" and the CLI stops being a thin client, gains a second source of truth,
 * and starts needing database credentials to do its job.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const sourceRoot = join(packageRoot, "src");

/** Runtimes the CLI may not reach for. Execution lives server-side (docs/25). */
const FORBIDDEN = [
  "playwright",
  "temporalio",
  "@temporalio",
  "langgraph",
  "langchain",
  "pg",
  "postgres",
  "redis",
  "ioredis",
  "openai",
  "vllm",
];

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return path.endsWith(".ts") ? [path] : [];
  });
}

function importedModules(path: string): string[] {
  const source = readFileSync(path, "utf8");
  const modules: string[] = [];
  // Static imports, re-exports and dynamic import() alike: a dynamic import is still
  // a dependency, and only checking the static form would leave the obvious hole.
  for (const match of source.matchAll(/(?:from|import)\s*\(?\s*["']([^"']+)["']/g)) {
    if (match[1] !== undefined) modules.push(match[1]);
  }
  for (const match of source.matchAll(/require\(\s*["']([^"']+)["']\s*\)/g)) {
    if (match[1] !== undefined) modules.push(match[1]);
  }
  return modules;
}

function packageName(specifier: string): string {
  if (specifier.startsWith(".") || specifier.startsWith("node:")) return "";
  const parts = specifier.split("/");
  return specifier.startsWith("@") ? `${parts[0]}/${parts[1]}` : (parts[0] ?? "");
}

describe("delivery boundary", () => {
  it("never imports a runtime that belongs on the server", () => {
    const violations = sourceFiles(sourceRoot).flatMap((path) =>
      importedModules(path)
        .filter((specifier) => FORBIDDEN.includes(packageName(specifier)))
        .map((specifier) => `${path} imports ${specifier}`),
    );

    expect(violations).toEqual([]);
  });

  it("catches a planted violation, so the guard is not vacuous", () => {
    // A check that cannot fail proves nothing.
    const planted = ['import { Client } from "pg";', 'const x = await import("playwright");'];

    for (const line of planted) {
      const found = [...line.matchAll(/(?:from|import)\s*\(?\s*["']([^"']+)["']/g)]
        .map((match) => packageName(match[1] ?? ""))
        .filter((name) => FORBIDDEN.includes(name));
      expect(found.length).toBeGreaterThan(0);
    }
  });

  it("declares no server runtime as a dependency either", () => {
    // An import guard alone would miss a dependency added "for later".
    const manifest: unknown = JSON.parse(
      readFileSync(join(packageRoot, "package.json"), "utf8"),
    );
    const declared = Object.keys(
      (manifest as { dependencies?: Record<string, string> }).dependencies ?? {},
    );

    expect(declared.filter((name) => FORBIDDEN.includes(name))).toEqual([]);
  });
});
