/**
 * The Phase 10 gate: **Views do not import API clients.**
 *
 * Enforced by reading the import lines rather than by convention, because the failure
 * it prevents is invisible in review — one `fetch` in a component works fine, and by
 * the time there are ten the layering is gone and nothing can be tested without a
 * network.
 *
 * The same scan covers the rest of the direction docs/04 fixes: domain depends on
 * nothing, application depends only on domain, and neither knows React exists.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

// Resolved from the project root rather than from `import.meta.url`: under jsdom the
// module URL is not a file URL, so `fileURLToPath` has nothing to convert.
const SRC = resolve(process.cwd(), "src");

/** What each layer is not allowed to reach for, and why in one word. */
const FORBIDDEN: Record<string, readonly string[]> = {
  // A view that can fetch is a view nobody can test without a server, and a rule that
  // erodes one component at a time.
  views: ["@infrastructure/", "@application/ports", "fetch(", "WebSocket", "axios"],
  // ViewModels talk to ports. Naming a concrete adapter here would make swapping one
  // a change across every screen.
  viewmodels: ["@infrastructure/api/client", "@infrastructure/realtime/"],
  // Use cases and ports are plain logic: they have to run in a test with no DOM.
  application: ["react", "@views/", "@viewmodels/", "@infrastructure/"],
  // The domain is the one layer with no dependencies at all.
  domain: ["react", "zod", "@application/", "@infrastructure/", "@viewmodels/", "@views/"],
};

/** The composition root is the one place allowed to know both sides. */
const COMPOSITION_ROOT = ["viewmodels/gateways.ts"];

function sourceFiles(directory: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) {
      found.push(...sourceFiles(path));
    } else if (/\.tsx?$/.test(entry)) {
      found.push(path);
    }
  }
  return found;
}

function relative(path: string): string {
  return path.slice(SRC.length + 1).replaceAll("\\", "/");
}

function offendersIn(layer: string, forbidden: readonly string[]): string[] {
  const offenders: string[] = [];
  for (const file of sourceFiles(join(SRC, layer))) {
    const name = relative(file);
    if (COMPOSITION_ROOT.includes(name)) continue;
    const text = readFileSync(file, "utf8");
    for (const needle of forbidden) {
      if (text.includes(needle)) offenders.push(`${name} → ${needle}`);
    }
  }
  return offenders;
}

describe("layer boundaries", () => {
  for (const [layer, forbidden] of Object.entries(FORBIDDEN)) {
    it(`${layer} reaches for nothing below it`, () => {
      expect(offendersIn(layer, forbidden)).toEqual([]);
    });
  }

  it("only the composition root names a concrete adapter", () => {
    const named = sourceFiles(SRC)
      .map(relative)
      .filter((name) => !name.startsWith("infrastructure/"))
      .filter((name) => {
        const text = readFileSync(join(SRC, name), "utf8");
        return text.includes("HttpRunGateway") || text.includes("WebSocketRunEventStream");
      });

    expect(named).toEqual(COMPOSITION_ROOT);
  });

  it("catches a planted violation", () => {
    // A guard that cannot fail proves nothing.
    const planted = "views/leaky.tsx";
    const text = 'const data = await fetch("/api/v1/runs");';
    expect(FORBIDDEN.views?.some((needle) => text.includes(needle))).toBe(true);
    expect(planted).toContain("views/");
  });
});
