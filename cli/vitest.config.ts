import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    // Subprocess contract tests spawn a real node process each time.
    testTimeout: 30_000,
  },
});
