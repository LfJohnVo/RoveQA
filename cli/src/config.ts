/**
 * Configuration resolution, with the precedence the docs promise:
 *
 *     command flag > environment variable > project config > user config > default
 *
 * Each layer records where its value came from, because "why is it talking to the
 * wrong server" is the question this file exists to answer in one command.
 *
 * Project config is version-controlled, so it may name endpoints and identifiers and
 * nothing else. A token read from a tracked file would be a token in the repository
 * (docs/13), so only the environment and the user config may carry one.
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";

import { CliError } from "./errors.js";

export const DEFAULT_API_URL = "http://localhost:8000";
export const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

export interface Config {
  apiUrl: string;
  projectId: string | null;
  environmentId: string | null;
  token: string | null;
  requestTimeoutMs: number;
  /** Where each resolved value came from, for `doctor`. */
  sources: Record<string, string>;
}

export interface ConfigFlags {
  apiUrl?: string | undefined;
  projectId?: string | undefined;
  environmentId?: string | undefined;
  requestTimeoutMs?: number | undefined;
}

interface FileConfig {
  api_url?: unknown;
  project_id?: unknown;
  environment_id?: unknown;
  token?: unknown;
  request_timeout_ms?: unknown;
}

export const PROJECT_CONFIG_NAME = ".roveqa/config.json";
export const USER_CONFIG_NAME = ".roveqa/config.json";

/** Secrets are refused from tracked config rather than quietly honoured. */
const PROJECT_FORBIDDEN_KEYS = ["token"] as const;

export function loadConfig(
  flags: ConfigFlags,
  env: NodeJS.ProcessEnv = process.env,
  cwd: string = process.cwd(),
): Config {
  const project = readProjectConfig(cwd);
  const user = readUserConfig(env);
  const sources: Record<string, string> = {};

  const pick = <T>(
    name: string,
    layers: Array<{ from: string; value: T | undefined | null }>,
    fallback: T,
  ): T => {
    for (const layer of layers) {
      if (layer.value !== undefined && layer.value !== null && layer.value !== "") {
        sources[name] = layer.from;
        return layer.value;
      }
    }
    sources[name] = "default";
    return fallback;
  };

  const apiUrl = pick(
    "api_url",
    [
      { from: "flag", value: flags.apiUrl },
      { from: "env:ROVEQA_API_URL", value: env.ROVEQA_API_URL },
      { from: `project:${PROJECT_CONFIG_NAME}`, value: asString(project.config.api_url) },
      { from: `user:${user.path ?? USER_CONFIG_NAME}`, value: asString(user.config.api_url) },
    ],
    DEFAULT_API_URL,
  );

  const projectId = pick<string | null>(
    "project_id",
    [
      { from: "flag", value: flags.projectId },
      { from: "env:ROVEQA_PROJECT_ID", value: env.ROVEQA_PROJECT_ID },
      { from: `project:${PROJECT_CONFIG_NAME}`, value: asString(project.config.project_id) },
      { from: `user:${user.path ?? USER_CONFIG_NAME}`, value: asString(user.config.project_id) },
    ],
    null,
  );

  const environmentId = pick<string | null>(
    "environment_id",
    [
      { from: "flag", value: flags.environmentId },
      { from: "env:ROVEQA_ENVIRONMENT_ID", value: env.ROVEQA_ENVIRONMENT_ID },
      { from: `project:${PROJECT_CONFIG_NAME}`, value: asString(project.config.environment_id) },
      {
        from: `user:${user.path ?? USER_CONFIG_NAME}`,
        value: asString(user.config.environment_id),
      },
    ],
    null,
  );

  // No flag layer: a token on the command line lands in shell history and in the
  // process list of every other user on the machine.
  const token = pick<string | null>(
    "token",
    [
      { from: "env:ROVEQA_TOKEN", value: env.ROVEQA_TOKEN },
      { from: `user:${user.path ?? USER_CONFIG_NAME}`, value: asString(user.config.token) },
    ],
    null,
  );

  const requestTimeoutMs = pick(
    "request_timeout_ms",
    [
      { from: "flag", value: flags.requestTimeoutMs },
      { from: "env:ROVEQA_REQUEST_TIMEOUT_MS", value: asPositiveInt(env.ROVEQA_REQUEST_TIMEOUT_MS) },
      {
        from: `project:${PROJECT_CONFIG_NAME}`,
        value: asPositiveInt(project.config.request_timeout_ms),
      },
      {
        from: `user:${user.path ?? USER_CONFIG_NAME}`,
        value: asPositiveInt(user.config.request_timeout_ms),
      },
    ],
    DEFAULT_REQUEST_TIMEOUT_MS,
  );

  return { apiUrl, projectId, environmentId, token, requestTimeoutMs, sources };
}

/** Search upward for a project config, so the CLI works from any subdirectory. */
function readProjectConfig(cwd: string): { path: string | null; config: FileConfig } {
  let directory = resolve(cwd);
  for (;;) {
    const candidate = join(directory, PROJECT_CONFIG_NAME);
    const config = readJsonIfPresent(candidate);
    if (config !== null) {
      for (const key of PROJECT_FORBIDDEN_KEYS) {
        if (config[key] !== undefined) {
          throw new CliError(
            "CONFIG_ERROR",
            `${candidate} may not contain "${key}": project config is version-controlled`,
            { nextAction: `Move ${key} to ROVEQA_TOKEN or to the user config.` },
          );
        }
      }
      return { path: candidate, config };
    }
    const parent = dirname(directory);
    if (parent === directory) return { path: null, config: {} };
    directory = parent;
  }
}

function readUserConfig(env: NodeJS.ProcessEnv): { path: string | null; config: FileConfig } {
  const home = env.ROVEQA_HOME ?? homedir();
  const candidate = join(home, USER_CONFIG_NAME);
  const config = readJsonIfPresent(candidate);
  return config === null ? { path: null, config: {} } : { path: candidate, config };
}

function readJsonIfPresent(path: string): FileConfig | null {
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("config must be a JSON object");
    }
    return parsed;
  } catch (error) {
    // A corrupt config is reported, never ignored: silently falling back to defaults
    // would send the command at a different server than the operator believes.
    throw new CliError("CONFIG_ERROR", `${path} is not valid JSON: ${describe(error)}`);
  }
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value !== "" ? value : undefined;
}

function asPositiveInt(value: unknown): number | undefined {
  const parsed = typeof value === "string" ? Number(value) : value;
  return typeof parsed === "number" && Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
