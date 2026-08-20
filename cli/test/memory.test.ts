/**
 * `roveqa memory …` against a stub server.
 *
 * These commands are the ones an operator runs when something is already wrong, so
 * what is under test is mostly refusal: a malformed answer must surface as a
 * transport error rather than be rendered into a report that reads healthy.
 */

import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { ApiClient } from "../src/client/api.js";
import { CliError } from "../src/errors.js";
import {
  memoryRebuild,
  memoryStatus,
  memoryValidate,
  parseStatus,
  renderRebuild,
  renderStatus,
  renderValidation,
} from "../src/commands/memory.js";

interface Stub {
  client: ApiClient;
  urls: string[];
  methods: string[];
  close: () => Promise<void>;
}

async function stubServer(body: unknown, status = 200): Promise<Stub> {
  const urls: string[] = [];
  const methods: string[] = [];
  const server: Server = createServer((incoming, response) => {
    urls.push(incoming.url ?? "");
    methods.push(incoming.method ?? "");
    incoming.on("data", () => undefined);
    incoming.on("end", () => {
      response.writeHead(status, { "content-type": "application/json" });
      response.end(JSON.stringify(body));
    });
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;
  return {
    urls,
    methods,
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

function status(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    project_id: "proj-1",
    environment_id: "staging",
    graph_available: true,
    graph_schema_version: "roveqa.graph.v1",
    durable_candidates: 12,
    actionable_candidates: 5,
    sync_pending: 0,
    sync_failed: 0,
    by_status: { candidate: 7, promoted: 4, trusted: 1 },
    ...overrides,
  };
}

describe("scope", () => {
  it("asks about one project and environment, never all of them", async () => {
    // A rebuild that guessed the scope could rewrite the wrong project's projection.
    open = await stubServer(status());

    await memoryStatus(open.client, "proj-1", "staging");

    expect(open.urls[0]).toBe("/api/v1/projects/proj-1/memory/status?environment_id=staging");
  });

  it("escapes identifiers instead of pasting them into the path", async () => {
    // An id with a slash would otherwise address a different route entirely.
    open = await stubServer(status());

    await memoryStatus(open.client, "proj/1?x=y", "staging");

    expect(open.urls[0]).toContain("/projects/proj%2F1%3Fx%3Dy/memory/status");
  });

  it("rebuild is a POST, status is not", async () => {
    open = await stubServer({
      project_id: "proj-1",
      environment_id: "staging",
      materialized: 3,
      forgotten: 1,
      failed: 0,
      graph_available: true,
    });

    await memoryRebuild(open.client, "proj-1", "staging");

    expect(open.methods[0]).toBe("POST");
  });
});

describe("a malformed answer is refused", () => {
  it("rejects a status that is not an object", async () => {
    open = await stubServer(["not", "a", "status"]);
    await expect(memoryStatus(open.client, "proj-1", "staging")).rejects.toBeInstanceOf(CliError);
  });

  it("rejects a missing count rather than rendering undefined", async () => {
    // The number an operator reads to decide whether to rebuild.
    const broken = status();
    delete broken.sync_pending;
    open = await stubServer(broken);

    await expect(memoryStatus(open.client, "proj-1", "staging")).rejects.toBeInstanceOf(CliError);
  });

  it("rejects a non-boolean availability flag", async () => {
    open = await stubServer(status({ graph_available: "yes" }));
    await expect(memoryStatus(open.client, "proj-1", "staging")).rejects.toBeInstanceOf(CliError);
  });

  it("rejects problems that are not strings", async () => {
    open = await stubServer({
      project_id: "proj-1",
      environment_id: "staging",
      healthy: false,
      problems: [{ oops: true }],
      status: status(),
    });

    await expect(memoryValidate(open.client, "proj-1", "staging")).rejects.toBeInstanceOf(CliError);
  });
});

describe("what the operator reads", () => {
  it("says the graph is unavailable in capitals rather than burying it", () => {
    const rendered = renderStatus(parseStatus(status({ graph_available: false })));
    expect(rendered).toContain("UNAVAILABLE");
  });

  it("separates durable knowledge from what the projection holds", () => {
    // One number could not say that the graph is empty but the knowledge is safe.
    const rendered = renderStatus(parseStatus(status({ sync_pending: 9 })));
    expect(rendered).toContain("12 durable");
    expect(rendered).toContain("9 pending");
  });

  it("names each problem instead of counting them", () => {
    const rendered = renderValidation({
      project_id: "proj-1",
      environment_id: "staging",
      healthy: false,
      problems: ["graph store unreachable"],
      status: parseStatus(status({ graph_available: false })),
    });
    expect(rendered).toContain("graph store unreachable");
  });

  it("tells the operator the work was kept when the graph was down", () => {
    const rendered = renderRebuild({
      project_id: "proj-1",
      environment_id: "staging",
      materialized: 0,
      forgotten: 0,
      failed: 1,
      graph_available: false,
    });
    expect(rendered).toContain("the backlog kept the work");
  });
});
