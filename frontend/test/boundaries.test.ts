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

/** Every module this file imports, by specifier. */
function importsOf(text: string): string[] {
  const found: string[] = [];
  const pattern = /(?:from|import)\s+["']([^"']+)["']/g;
  for (const match of text.matchAll(pattern)) {
    if (match[1] !== undefined) found.push(match[1]);
  }
  return found;
}

/**
 * A needle naming a module is checked against the *imports*; one naming a call is
 * checked against the text.
 *
 * The distinction is not pedantry. `text.includes("react")` matched the word "reached"
 * in a domain file's comment and failed the build — so the guard's real cost was that
 * people would learn to reword prose around it, which is how a guard stops being
 * believed. `fetch(` and `WebSocket` stay textual because they are not imports; there is
 * nothing else they could be.
 */
function isModuleNeedle(needle: string): boolean {
  return !needle.includes("(") && needle !== "WebSocket";
}

function offendersIn(layer: string, forbidden: readonly string[]): string[] {
  const offenders: string[] = [];
  for (const file of sourceFiles(join(SRC, layer))) {
    const name = relative(file);
    if (COMPOSITION_ROOT.includes(name)) continue;
    const text = readFileSync(file, "utf8");
    const specifiers = importsOf(text);
    for (const needle of forbidden) {
      const offends = isModuleNeedle(needle)
        ? specifiers.some(
            (specifier) => specifier === needle || specifier.startsWith(needle),
          )
        : text.includes(needle);
      if (offends) offenders.push(`${name} → ${needle}`);
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
    // A guard that cannot fail proves nothing. Both kinds of needle are planted, because
    // the two are now checked differently.
    const fetching = 'const data = await fetch("/api/v1/runs");';
    expect(FORBIDDEN.views?.some((needle) => fetching.includes(needle))).toBe(true);

    const importing = 'import { HttpRunGateway } from "@infrastructure/api/client";';
    expect(importsOf(importing)).toContain("@infrastructure/api/client");
    expect(
      FORBIDDEN.views
        ?.filter(isModuleNeedle)
        .some((needle) => importsOf(importing).some((s) => s.startsWith(needle))),
    ).toBe(true);
  });

  it("does not fire on prose that merely contains a module name", () => {
    // "reached" contains "react". A domain file's comment failed the build on that, and a
    // guard people reword their comments around is one they will eventually route around.
    const prose = "/** What a traversal reached, and the reaction to it. */";

    expect(importsOf(prose)).toEqual([]);
  });
});
