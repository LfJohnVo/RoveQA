/**
 * `roveqa session register|list|revoke` — lend a run a session, and take it back.
 *
 * The point of these commands is that a credential never has to be pasted into a
 * fixture, a repository or a compose file to make an authenticated run work. It is read
 * from a file the operator exported from their own browser, sent once, and sealed on the
 * other side (ADR 0019).
 *
 * Nothing here can read one back. There is no `session show`, and there is no endpoint
 * behind it — a stored session goes in and never comes out, which is the whole
 * containment argument and would be undone by one convenience command.
 */

import { readFileSync, statSync } from "node:fs";

import type { ApiClient } from "../client/api.js";
import { CliError } from "../errors.js";

export const MAX_STORAGE_STATE_BYTES = 512_000;
/**
 * A storage state is cookies and origin storage — kilobytes. Bounded here as well as on
 * the server because a CLI that reads a two-gigabyte file into memory before finding out
 * the server refuses it has already done the damage (docs/25).
 */

export interface SessionRecord {
  session_id: string;
  environment_id: string;
  label: string;
  established_at: string;
  valid_until: string | null;
  established_by: string;
}

function record(value: unknown, what: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new CliError("TRANSPORT_ERROR", `the server returned a ${what} that is not an object`);
  }
  return value as Record<string, unknown>;
}

function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new CliError("TRANSPORT_ERROR", `the server returned an empty ${key}`);
  }
  return value;
}

export function parseSession(value: unknown): SessionRecord {
  const body = record(value, "session");
  const validUntil = body.valid_until;
  if (validUntil !== null && validUntil !== undefined && typeof validUntil !== "string") {
    throw new CliError("TRANSPORT_ERROR", "the server returned a non-string valid_until");
  }
  const establishedBy = body.established_by;
  return {
    session_id: text(body, "session_id"),
    environment_id: text(body, "environment_id"),
    label: text(body, "label"),
    established_at: text(body, "established_at"),
    valid_until: typeof validUntil === "string" ? validUntil : null,
    established_by: typeof establishedBy === "string" ? establishedBy : "",
  };
}

export function parseSessions(value: unknown): SessionRecord[] {
  if (!Array.isArray(value)) {
    throw new CliError("TRANSPORT_ERROR", "the server returned a session list that is not an array");
  }
  return value.map(parseSession);
}

/** Read the exported storage state, bounded, with errors a person can act on. */
export function readStorageState(path: string): string {
  let size: number;
  try {
    const info = statSync(path);
    if (info.isDirectory()) {
      throw new CliError("VALIDATION_ERROR", `session path is a directory, not a file: ${path}`);
    }
    size = info.size;
  } catch (error) {
    if (error instanceof CliError) throw error;
    throw new CliError("NOT_FOUND", `cannot read session file: ${path}`, {
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }
  if (size > MAX_STORAGE_STATE_BYTES) {
    throw new CliError(
      "VALIDATION_ERROR",
      `session file exceeds ${MAX_STORAGE_STATE_BYTES} bytes: ${path}`,
    );
  }

  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (error) {
    throw new CliError("NOT_FOUND", `cannot read session file: ${path}`, {
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }
  try {
    JSON.parse(raw);
  } catch (error) {
    // Checked here rather than left to the server, because the server's 422 would have
    // to quote what it could not parse — and what it could not parse is the session.
    throw new CliError("VALIDATION_ERROR", `session file is not valid JSON: ${path}`, {
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }
  return raw;
}

export interface RegisterSessionInput {
  environmentId: string;
  label: string;
  storageState: string;
  validUntil?: string;
  establishedBy?: string;
}

function sessionsPath(environmentId: string): string {
  return `/api/v1/environments/${encodeURIComponent(environmentId)}/sessions`;
}

export async function registerSession(
  client: ApiClient,
  input: RegisterSessionInput,
): Promise<SessionRecord> {
  const response = await client.request({
    method: "POST",
    path: sessionsPath(input.environmentId),
    body: {
      label: input.label,
      storage_state: input.storageState,
      ...(input.validUntil === undefined ? {} : { valid_until: input.validUntil }),
      ...(input.establishedBy === undefined ? {} : { established_by: input.establishedBy }),
    },
  });
  return parseSession(response.body);
}

export async function listSessions(
  client: ApiClient,
  environmentId: string,
): Promise<SessionRecord[]> {
  const response = await client.request({ method: "GET", path: sessionsPath(environmentId) });
  return parseSessions(response.body);
}

export async function revokeSession(
  client: ApiClient,
  environmentId: string,
  sessionId: string,
): Promise<void> {
  // A command, not a delete: the record stays as the audit trail and the key is what
  // gets destroyed. Naming it `delete` here would promise the row disappears.
  await client.request({
    method: "POST",
    path: `${sessionsPath(environmentId)}/${encodeURIComponent(sessionId)}/revoke`,
  });
}

export function renderSessions(sessions: readonly SessionRecord[]): string {
  if (sessions.length === 0) {
    return "No sessions registered. Runs against this environment go out anonymous.";
  }
  const lines = sessions.map((session) => {
    const expiry = session.valid_until === null ? "no stated expiry" : `until ${session.valid_until}`;
    return `- ${session.label} (${session.session_id}) — established ${session.established_at}, ${expiry}`;
  });
  return [`${sessions.length} session(s):`, ...lines].join("\n");
}
