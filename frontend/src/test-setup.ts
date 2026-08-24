import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

/**
 * Unmount between tests.
 *
 * Testing Library registers this itself only when vitest runs with globals, and this
 * project does not. Without it every render stays in the document: queries then match
 * a previous test's markup, and the failures look like flakiness rather than like the
 * leak they are.
 */
afterEach(() => {
  cleanup();
});

/**
 * jsdom has no `matchMedia`.
 *
 * Stubbed here rather than guarded in the code that calls it: a browser always has it,
 * and a branch that exists only to satisfy a fake environment is a branch nothing real
 * ever takes. Light by default, so a test that cares about the dark theme says so.
 */
window.matchMedia = ((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener: () => undefined,
  removeEventListener: () => undefined,
  addListener: () => undefined,
  removeListener: () => undefined,
  dispatchEvent: () => false,
})) as typeof window.matchMedia;
