/**
 * Run lifecycle contracts, driven against a stub server in this process.
 *
 * A stub rather than the real API because what is under test here is the *client's*
 * behaviour: which requests it retries, which it does not, what it does when a
 * deadline expires. Those are properties of this code, and a real backend would make
 * them slower to observe and harder to provoke.
 */

import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { ApiClient } from "../src/client/api.js";
import { CliError } from "../src/errors.js";
import { doctor, problemError } from "../src/commands/doctor.js";
import { cancelRun, createRun, getRun, waitForRun } from "../src/commands/run.js";

interface RecordedRequest {
  method: string;
  url: string;
  headers: Record<string, string | undefined>;
  body: string;
}

interface Stub {
  client: ApiClient;
  requests: RecordedRequest[];
  close: () => Promise<void>;
}

type Handler = (request: RecordedRequest, index: number) => { status: number; body: unknown };

async function stubServer(handler: Handler): Promise<Stub> {
  const requests: RecordedRequest[] = [];
  const server: Server = createServer((incoming, response) => {
    let body = "";
    incoming.on("data", (chunk: Buffer) => (body += chunk.toString()));
    incoming.on("end", () => {
      const recorded: RecordedRequest = {
        method: incoming.method ?? "",
        url: incoming.url ?? "",
        headers: incoming.headers as Record<string, string | undefined>,
        body,
      };
      requests.push(recorded);
      const result = handler(recorded, requests.length - 1);
      response.writeHead(result.status, { "content-type": "application/json" });
      response.end(JSON.stringify(result.body));
    });
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;

  return {
    requests,
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

function running(runId = "run-1"): Record<string, unknown> {
  return { run_id: runId, status: "running", verdict: null, plan_id: "p", plan_version: "1" };
}

function completed(verdict: string, runId = "run-1"): Record<string, unknown> {
  return { run_id: runId, status: "completed", verdict, plan_id: "p", plan_version: "1" };
}

describe("idempotency", () => {
  it("sends a key with every run creation", async () => {
    open = await stubServer(() => ({ status: 201, body: completed("passed") }));

    await createRun(open.client, { projectId: "p-1", planId: "plan-1", planVersion: "1" });

    expect(open.requests[0]?.headers["idempotency-key"]).toBeTruthy();
  });

  it("reuses the same key when a lost response is retried", async () => {
    // The server drops the first answer. The retry must be recognisable as the same
    // request, or the client turns one intended run into two.
    open = await stubServer((_request, index) =>
      index === 0 ? { status: 503, body: {} } : { status: 201, body: completed("passed") },
    );

    await createRun(open.client, { projectId: "p-1", planId: "plan-1", planVersion: "1" });

    expect(open.requests).toHaveLength(2);
    expect(open.requests[0]?.headers["idempotency-key"]).toBe(
      open.requests[1]?.headers["idempotency-key"],
    );
  });

  it("does not retry a conflict", async () => {
    // A 409 is an answer. Asking again asks the same question.
    open = await stubServer(() => ({ status: 409, body: { detail: "key reused" } }));

    await expect(
      createRun(open.client, { projectId: "p-1", planId: "plan-1", planVersion: "1" }),
    ).rejects.toMatchObject({ code: "CONFLICT" });
    expect(open.requests).toHaveLength(1);
  });

  it("propagates one request id across every attempt", async () => {
    open = await stubServer((_request, index) =>
      index === 0 ? { status: 503, body: {} } : { status: 200, body: completed("passed") },
    );

    await getRun(open.client, "run-1");

    expect(open.requests.map((request) => request.headers["x-request-id"])).toEqual([
      "req-1",
      "req-1",
    ]);
  });
});

describe("waiting", () => {
  it("returns the verdict once the run is terminal", async () => {
    open = await stubServer((_request, index) =>
      index < 2 ? { status: 200, body: running() } : { status: 200, body: completed("failed") },
    );

    const outcome = await waitForRun(open.client, "run-1", {
      pollIntervalMs: 1,
      timeoutMs: 10_000,
      sleep: () => Promise.resolve(),
    });

    expect(outcome.timedOut).toBe(false);
    expect(outcome.verdict).toBe("failed");
  });

  it("detaches when the client deadline expires, leaving the run alone", async () => {
    // The assertion that matters is the last one: nothing was sent to stop the run.
    open = await stubServer(() => ({ status: 200, body: running() }));

    const outcome = await waitForRun(open.client, "run-1", {
      pollIntervalMs: 1_000,
      timeoutMs: 0,
      sleep: () => Promise.resolve(),
    });

    expect(outcome.timedOut).toBe(true);
    expect(outcome.verdict).toBeNull();
    expect(open.requests.every((request) => request.method === "GET")).toBe(true);
  });

  it("detaches on an abort signal without cancelling", async () => {
    open = await stubServer(() => ({ status: 200, body: running() }));
    const controller = new AbortController();
    controller.abort();

    const outcome = await waitForRun(open.client, "run-1", {
      signal: controller.signal,
      pollIntervalMs: 1,
      sleep: () => Promise.resolve(),
    });

    expect(outcome.timedOut).toBe(true);
    expect(open.requests.some((request) => request.url.includes("cancel"))).toBe(false);
  });

  it("only cancels when asked to", async () => {
    open = await stubServer(() => ({ status: 202, body: { run_id: "run-1", accepted: true } }));

    await cancelRun(open.client, "run-1");

    expect(open.requests[0]?.method).toBe("POST");
    expect(open.requests[0]?.url).toContain("/cancel");
  });
});

describe("response validation", () => {
  it("refuses a verdict it does not recognise", async () => {
    // The exit code is derived from the verdict, so an unknown value must not pass
    // through as "not passed".
    open = await stubServer(() => ({
      status: 200,
      body: { run_id: "run-1", status: "completed", verdict: "probably-fine" },
    }));

    await expect(getRun(open.client, "run-1")).rejects.toThrow(CliError);
  });

  it("refuses a body that is not a run", async () => {
    open = await stubServer(() => ({ status: 200, body: { unexpected: true } }));

    await expect(getRun(open.client, "run-1")).rejects.toMatchObject({
      code: "TRANSPORT_ERROR",
    });
  });
});

describe("transport", () => {
  it("maps a missing run to NOT_FOUND", async () => {
    open = await stubServer(() => ({ status: 404, body: { detail: "run not found" } }));

    await expect(getRun(open.client, "missing")).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("reports an unreachable server with a next action", async () => {
    const client = new ApiClient({
      // Nothing listens here; the port is closed rather than firewalled so this fails
      // fast instead of waiting for the timeout.
      baseUrl: "http://127.0.0.1:1",
      token: null,
      requestId: "req-1",
      timeoutMs: 500,
      sleep: () => Promise.resolve(),
    });

    await expect(client.request({ method: "GET", path: "/health" })).rejects.toMatchObject({
      code: "TRANSPORT_ERROR",
    });
  });
});

describe("doctor", () => {
  it("fails when the API is unreachable, so CI cannot pass on a broken setup", async () => {
    const client = new ApiClient({
      baseUrl: "http://127.0.0.1:1",
      token: null,
      requestId: "req-1",
      timeoutMs: 500,
      sleep: () => Promise.resolve(),
    });
    const config = {
      apiUrl: "http://127.0.0.1:1",
      projectId: "p-1",
      environmentId: null,
      token: null,
      requestTimeoutMs: 500,
      sources: {},
    };

    const report = await doctor(client, config, "0.1.0");
    const failure = problemError(report);

    expect(report.api_reachable).toBe(false);
    expect(failure?.code).toBe("TRANSPORT_ERROR");
    // The whole report survives the failure, so nothing is lost by exiting non-zero.
    expect((failure?.details as { report: { problems: string[] } }).report.problems).toHaveLength(1);
  });

  it("passes when everything is configured and reachable", async () => {
    // A healthy server answers both: reachability and which contracts it speaks.
    open = await stubServer((request) =>
      request.url === "/api/v1/meta/contracts"
        ? { status: 200, body: { contracts: { test_plan: "roveqa.test-plan.v1" } } }
        : { status: 200, body: { status: "ok" } },
    );
    const config = {
      apiUrl: "http://127.0.0.1",
      projectId: "p-1",
      environmentId: null,
      token: null,
      requestTimeoutMs: 500,
      sources: {},
    };

    const report = await doctor(open.client, config, "0.1.0");

    expect(problemError(report)).toBeNull();
  });
});

describe("contract compatibility", () => {
  function reachable(contracts: Record<string, string> | null): Handler {
    return (request) => {
      if (request.url === "/health") return { status: 200, body: { status: "ok" } };
      if (request.url === "/api/v1/meta/contracts") {
        return contracts === null
          ? { status: 404, body: { detail: "not found" } }
          : { status: 200, body: { api_version: "v1", contracts } };
      }
      return { status: 404, body: {} };
    };
  }

  const config = {
    apiUrl: "http://127.0.0.1",
    projectId: "p-1",
    environmentId: null,
    token: null,
    requestTimeoutMs: 500,
    sources: {},
  };

  it("passes when the CLI and the server speak the same contracts", async () => {
    open = await stubServer(reachable({ test_plan: "roveqa.test-plan.v1" }));

    const report = await doctor(open.client, config, "0.1.0");

    expect(report.api_contracts).toEqual({ test_plan: "roveqa.test-plan.v1" });
    expect(problemError(report)).toBeNull();
  });

  it("reports a mismatch rather than adapting to it", async () => {
    // A CLI that silently adapts produces output whose meaning depends on which
    // server it happened to reach.
    open = await stubServer(reachable({ test_plan: "roveqa.test-plan.v2" }));

    const report = await doctor(open.client, config, "0.1.0");

    expect(problemError(report)?.code).toBe("CONFIG_ERROR");
    expect(report.problems.join(" ")).toContain("plan contract mismatch");
  });

  it("says compatibility is unverified against a server too old to report it", async () => {
    // Not the same as agreement: an unanswerable question is reported as one.
    open = await stubServer(reachable(null));

    const report = await doctor(open.client, config, "0.1.0");

    expect(report.api_contracts).toBeNull();
    expect(report.problems.join(" ")).toContain("compatibility is unverified");
  });
});
