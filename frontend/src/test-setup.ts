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
