/**
 * `roveqa setup` — write the project config and nothing else.
 *
 * It creates a local file. It does not phone home, register anything, or require an
 * account: a self-hosted tool whose setup step needed a cloud service would not be
 * self-hosted (docs/25).
 *
 * The file is version-controlled, so it may hold endpoints and identifiers only. A
 * token is refused here for the same reason `loadConfig` refuses to read one: writing
 * it would put a secret in the repository, and the mistake is much easier to make
 * than to notice.
 */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import { CliError } from "../errors.js";
import { PROJECT_CONFIG_NAME } from "../config.js";

export interface SetupInput {
  cwd: string;
  apiUrl?: string | undefined;
  projectId?: string | undefined;
  environmentId?: string | undefined;
}

export interface SetupResult {
  path: string;
  config: Record<string, string>;
  created: boolean;
}

export async function setup(input: SetupInput): Promise<SetupResult> {
  const path = join(input.cwd, PROJECT_CONFIG_NAME);
  const existing = await readExisting(path);

  // Merged, not overwritten: `roveqa setup --project X` must not silently drop an
  // api_url a colleague already committed.
  const config: Record<string, string> = { ...existing };
  if (input.apiUrl !== undefined) config.api_url = input.apiUrl;
  if (input.projectId !== undefined) config.project_id = input.projectId;
  if (input.environmentId !== undefined) config.environment_id = input.environmentId;

  if (Object.keys(config).length === 0) {
    throw new CliError("USAGE_ERROR", "nothing to write", {
      nextAction: "Pass at least one of --api-url, --project or --environment.",
    });
  }

  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(config, null, 2)}\n`);
  return { path, config, created: existing === null };
}

async function readExisting(path: string): Promise<Record<string, string> | null> {
  let raw: string;
  try {
    raw = await readFile(path, "utf8");
  } catch {
    return null;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // Overwriting a file we could not read would destroy whatever it held.
    throw new CliError("CONFIG_ERROR", `${path} is not valid JSON`, {
      nextAction: "Fix or delete it before running setup again.",
    });
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new CliError("CONFIG_ERROR", `${path} is not a JSON object`);
  }

  const entries = Object.entries(parsed as Record<string, unknown>);
  if (entries.some(([key]) => key === "token")) {
    throw new CliError("CONFIG_ERROR", `${path} contains a token`, {
      nextAction: "Remove it and use ROVEQA_TOKEN; this file is version-controlled.",
    });
  }
  return Object.fromEntries(
    entries.filter((entry): entry is [string, string] => typeof entry[1] === "string"),
  );
}
