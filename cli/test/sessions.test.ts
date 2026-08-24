/**
 * `roveqa session …` against a stub server.
 *
 * The property under test is what the CLI *sends* and what it refuses to accept back. A
 * session is the one thing this client handles that must never be printed, so the tests
 * check both directions: the state reaches the server intact, and nothing that comes back
 * is rendered into a line an operator could paste into a ticket.
 */

import { mkdtempSync, writeFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { ApiClient } from "../src/client/api.js";
import { CliError } from "../src/errors.js";
import {
  MAX_STORAGE_STATE_BYTES,
  listSessions,
  parseSession,
  readStorageState,
  registerSession,
  renderSessions,
  revokeSession,
  type SessionRecord,
} from "../src/commands/sessions.js";

const SECRET = "s3cr3t-session-value";
const STATE = JSON.stringify({ cookies: [{ name: "sid", value: SECRET }] });

interface Stub {
  client: ApiClient;
  urls: string[];
  methods: string[];
  bodies: string[];
  close: () => Promise<void>;
}

async function stubServer(body: unknown, status = 200): Promise<Stub> {
  const urls: string[] = [];
  const methods: string[] = [];
  const bodies: string[] = [];
  const server: Server = createServer((incoming, response) => {
    urls.push(incoming.url ?? "");
    methods.push(incoming.method ?? "");
    const chunks: Buffer[] = [];
    incoming.on("data", (chunk: Buffer) => chunks.push(chunk));
    incoming.on("end", () => {
      bodies.push(Buffer.concat(chunks).toString("utf8"));
      response.writeHead(status, { "content-type": "application/json" });
      response.end(JSON.stringify(body));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;
  return {
    urls,
    methods,
    bodies,
    client: new ApiClient({
      baseUrl: `http://127.0.0.1:${port}`,
      token: null,
      requestId: "req-1",
      timeoutMs: 2_000,
      sleep: () => Promise.resolve(),
    }),
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

let open: Stub | null = null;
afterEach(async () => {
  await open?.close();
  open = null;
});

function session(overrides: Partial<SessionRecord> = {}): Record<string, unknown> {
  return {
    session_id: "sess-1",
    environment_id: "env-1",
    label: "admin",
    established_at: "2026-08-23T10:00:00Z",
    valid_until: null,
    established_by: "captured by hand",
    ...overrides,
  };
}

function writeState(contents: string): string {
  const path = join(mkdtempSync(join(tmpdir(), "roveqa-session-")), "state.json");
  writeFileSync(path, contents, "utf8");
  return path;
}

describe("registering a session", () => {
  it("sends the state and gets back a record without it", async () => {
    open = await stubServer(session(), 201);

    const record = await registerSession(open.client, {
      environmentId: "env-1",
      label: "admin",
      storageState: STATE,
    });

    expect(open.methods).toEqual(["POST"]);
    expect(open.urls[0]).toBe("/api/v1/environments/env-1/sessions");
    // It goes out...
    expect(open.bodies[0]).toContain(SECRET);
    // ...and what comes back is a record.
    expect(record.session_id).toBe("sess-1");
    expect(JSON.stringify(record)).not.toContain(SECRET);
  });

  it("escapes an environment id rather than pasting it into a path", async () => {
    open = await stubServer(session(), 201);

    await registerSession(open.client, {
      environmentId: "env/../other",
      label: "admin",
      storageState: STATE,
    });

    expect(open.urls[0]).toBe("/api/v1/environments/env%2F..%2Fother/sessions");
  });

  it("refuses a file that is not JSON before sending anything", () => {
    // Checked here rather than left to the server, whose 422 would have to quote what it
    // could not parse — and what it could not parse is the session.
    const path = writeState("not json at all");

    expect(() => readStorageState(path)).toThrow(CliError);
  });

  it("refuses a file larger than a session could be", () => {
    const path = writeState("x".repeat(MAX_STORAGE_STATE_BYTES + 1));

    expect(() => readStorageState(path)).toThrow(/exceeds/);
  });

  it("says which file it could not read", () => {
    expect(() => readStorageState(join(tmpdir(), "nothing-here-at-all.json"))).toThrow(
      /cannot read session file/,
    );
  });

  it("reads a real exported state back unchanged", () => {
    const path = writeState(STATE);

    expect(readStorageState(path)).toBe(STATE);
  });
});

describe("listing and revoking", () => {
  it("lists records and renders none of their contents", async () => {
    open = await stubServer([session(), session({ session_id: "sess-2", label: "reviewer" })]);

    const sessions = await listSessions(open.client, "env-1");
    const rendered = renderSessions(sessions);

    expect(sessions).toHaveLength(2);
    expect(rendered).toContain("admin");
    expect(rendered).not.toContain(SECRET);
  });

  it("says plainly when an environment has none", () => {
    // An empty table reads as a load failure. A sentence says what will happen instead.
    expect(renderSessions([])).toContain("anonymous");
  });

  it("revokes with a command rather than a delete", async () => {
    // The record is not deleted — the key is. `DELETE` would promise the row disappears,
    // and a caller that listed afterwards would think the call failed.
    open = await stubServer({}, 204);

    await revokeSession(open.client, "env-1", "sess-1");

    expect(open.methods).toEqual(["POST"]);
    expect(open.urls[0]).toBe("/api/v1/environments/env-1/sessions/sess-1/revoke");
  });
});

describe("what the client refuses to believe", () => {
  it("rejects a session with no id", () => {
    expect(() => parseSession(session({ session_id: "" }))).toThrow(CliError);
  });

  it("rejects a list that is not a list", () => {
    open = null;
    expect(() => parseSession("a string")).toThrow(/not an object/);
  });

  it("treats an absent valid_until as no stated expiry", () => {
    // Absent and null mean the same thing here — nobody said when it ends — and that is
    // different from an expiry in the past.
    const record = parseSession({ ...session(), valid_until: undefined });

    expect(record.valid_until).toBeNull();
  });
});

describe("what a failed pipeline is told to do", () => {
  it("says how to get a token when there is none", async () => {
    // Found by running the CI drill: the job went red with `AUTH_REQUIRED` and
    // `next_action: null`, which is the one field an operator reads first.
    open = await stubServer({ error: { code: "AUTH_REQUIRED", message: "no token" } }, 401);

    const failure = await listSessions(open.client, "env-1").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(CliError);
    expect((failure as CliError).nextAction).toMatch(/ROVEQA_TOKEN/);
    expect((failure as CliError).nextAction).toMatch(/admin token issue/);
  });

  it("says which knob is wrong when the token is for another project", async () => {
    open = await stubServer({ error: { code: "FORBIDDEN", message: "not yours" } }, 403);

    const failure = await listSessions(open.client, "env-1").catch((error: unknown) => error);

    expect((failure as CliError).nextAction).toMatch(/ROVEQA_PROJECT_ID/);
  });

  it("stays silent where there is no single right answer", async () => {
    // A validation error can mean twenty things, and a guess printed as guidance is
    // worse than the silence it replaces.
    open = await stubServer({ error: { code: "VALIDATION_ERROR", message: "bad" } }, 422);

    const failure = await listSessions(open.client, "env-1").catch((error: unknown) => error);

    expect((failure as CliError).nextAction).toBeNull();
  });
});
