/**
 * Configuration precedence, which docs/25 promises and nobody can verify by reading.
 *
 *     command flag > environment variable > project config > user config > default
 */

import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { DEFAULT_API_URL, loadConfig } from "../src/config.js";
import { CliError } from "../src/errors.js";

function workspace(files: { project?: object; user?: object } = {}): {
  cwd: string;
  home: string;
} {
  const root = mkdtempSync(join(tmpdir(), "roveqa-config-"));
  const cwd = join(root, "repo");
  const home = join(root, "home");
  for (const [directory, config] of [
    [cwd, files.project],
    [home, files.user],
  ] as const) {
    mkdirSync(join(directory, ".roveqa"), { recursive: true });
    if (config) {
      writeFileSync(join(directory, ".roveqa", "config.json"), JSON.stringify(config));
    }
  }
  return { cwd, home };
}

describe("precedence", () => {
  it("prefers a flag over everything else", () => {
    const { cwd, home } = workspace({
      project: { api_url: "http://project.test" },
      user: { api_url: "http://user.test" },
    });

    const config = loadConfig(
      { apiUrl: "http://flag.test" },
      { ROVEQA_API_URL: "http://env.test", ROVEQA_HOME: home },
      cwd,
    );

    expect(config.apiUrl).toBe("http://flag.test");
    expect(config.sources.api_url).toBe("flag");
  });

  it("prefers the environment over config files", () => {
    const { cwd, home } = workspace({
      project: { api_url: "http://project.test" },
      user: { api_url: "http://user.test" },
    });

    const config = loadConfig({}, { ROVEQA_API_URL: "http://env.test", ROVEQA_HOME: home }, cwd);

    expect(config.apiUrl).toBe("http://env.test");
  });

  it("prefers project config over user config", () => {
    const { cwd, home } = workspace({
      project: { api_url: "http://project.test" },
      user: { api_url: "http://user.test" },
    });

    const config = loadConfig({}, { ROVEQA_HOME: home }, cwd);

    expect(config.apiUrl).toBe("http://project.test");
    expect(config.sources.api_url).toContain("project:");
  });

  it("falls back to the default and says so", () => {
    const { cwd, home } = workspace();

    const config = loadConfig({}, { ROVEQA_HOME: home }, cwd);

    expect(config.apiUrl).toBe(DEFAULT_API_URL);
    expect(config.sources.api_url).toBe("default");
  });

  it("finds the project config from a subdirectory", () => {
    const { cwd, home } = workspace({ project: { project_id: "p-1" } });
    const nested = join(cwd, "packages", "web");
    mkdirSync(nested, { recursive: true });

    expect(loadConfig({}, { ROVEQA_HOME: home }, nested).projectId).toBe("p-1");
  });
});

describe("secrets", () => {
  it("refuses a token in the version-controlled project config", () => {
    // Honouring it would mean a token committed to the repository works, which is
    // exactly the mistake that must fail loudly the first time.
    const { cwd, home } = workspace({ project: { token: "s3cret" } });

    expect(() => loadConfig({}, { ROVEQA_HOME: home }, cwd)).toThrow(CliError);
  });

  it("takes a token from the environment", () => {
    const { cwd, home } = workspace();

    const config = loadConfig({}, { ROVEQA_TOKEN: "s3cret", ROVEQA_HOME: home }, cwd);

    expect(config.token).toBe("s3cret");
    expect(config.sources.token).toBe("env:ROVEQA_TOKEN");
  });

  it("has no flag layer for the token", () => {
    // A token on the command line lands in shell history and the process list.
    const { cwd, home } = workspace();

    const config = loadConfig({}, { ROVEQA_HOME: home }, cwd);

    expect(config.token).toBeNull();
    expect(Object.keys(config.sources)).not.toContain("token_flag");
  });
});

describe("broken config", () => {
  it("reports corrupt JSON instead of silently using defaults", () => {
    const { cwd, home } = workspace();
    writeFileSync(join(cwd, ".roveqa", "config.json"), "{not json");

    expect(() => loadConfig({}, { ROVEQA_HOME: home }, cwd)).toThrow(/not valid JSON/);
  });
});
