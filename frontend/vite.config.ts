/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Layer aliases, kept in step with tsconfig.app.json.
 *
 * Two places have to agree because the compiler and the bundler resolve separately.
 * A boundary test reads the import strings, so a layer that moves without updating
 * both fails loudly rather than resolving by accident through a relative path. */
const layer = (name: string) => fileURLToPath(new URL(`./src/${name}`, import.meta.url));

const apiTarget = process.env.ROVEQA_API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@domain": layer("domain"),
      "@application": layer("application"),
      "@infrastructure": layer("infrastructure"),
      "@viewmodels": layer("viewmodels"),
      "@views": layer("views"),
    },
  },
  server: {
    // Inside compose the browser reaches this server as `http://frontend:5173`, and
    // Vite answers an unknown Host with a plain "Blocked request" page. Everything
    // still *works* — the navigation succeeds, a screenshot is captured, the run ends
    // `inconclusive` — so the only symptom is an agent that never finds anything on a
    // page that is not the application. That is what the demo bundle turned out to
    // contain. Listing the service name is what makes the target reachable by the name
    // the rest of the stack knows it by.
    allowedHosts: ["frontend", "localhost", "127.0.0.1"],

    // The API runs in compose; the dev server proxies so the browser talks to one
    // origin and no CORS configuration has to exist for development only.
    proxy: {
      "/api": { target: apiTarget, ws: true },
      // The realtime router is mounted at the root, not under /api/v1 (docs/12), so it
      // needs its own proxy entry. Reaching it through the REST prefix would 404.
      "/ws": { target: apiTarget, ws: true },
    },
    watch: {
      // A bind mount from a Windows host delivers no inotify events to the container,
      // so the dev server never notices an edit and every change needs a restart.
      // Opt-in rather than always on: polling costs CPU, and a Linux host does not
      // need it.
      usePolling: process.env.VITE_POLL_WATCH === "true",
      interval: 400,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "test/**/*.test.{ts,tsx}"],
  },
});
