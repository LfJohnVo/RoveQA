/**
 * `run flaky`: does a plan agree with itself?
 *
 * Driven against a stub server so the replay behaviour can be provoked directly. The
 * things worth defending are the ones that would silently produce a wrong answer: a
 * shared idempotency key (which would replay the same run and report perfect
 * stability), a timed-out replay folded in as a verdict, and moving memory left
 * unmentioned.
 */

import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { ApiClient } from "../src/client/api.js";
import { CliError } from "../src/errors.js";
import { measureFlakiness, validateCount, renderFlaky } from "../src/commands/flaky.js";

interface Recorded {
  method: string;
  url: string;
  idempotencyKey: string | undefined;
}

let server: Server | null = null;
afterEach(() => {
  server?.close();
  server = null;
});

/**
 * A server that gives each created run its own verdict, taken from `verdicts` in
 * order, and reports each criterion outcome from `criteria`.
 */
async function stub(
  verdicts: string[],
  criteria: Array<Array<{ criterion_id: string; outcome: string }>> = [],
): Promise<{ client: ApiClient; requests: Recorded[] }> {
  const requests: Recorded[] = [];
  const runVerdict = new Map<string, string>();
  const runCriteria = new Map<string, Array<{ criterion_id: string; outcome: string }>>();
  let created = 0;

  server = createServer((incoming, response) => {
    const url = incoming.url ?? "";
    requests.push({
      method: incoming.method ?? "",
      url,
      idempotencyKey: incoming.headers["idempotency-key"] as string | undefined,
    });

    const reply = (status: number, body: unknown): void => {
      response.writeHead(status, { "content-type": "application/json" });
      response.end(JSON.stringify(body));
    };

    if (incoming.method === "POST" && url === "/api/v1/runs") {
      const runId = `run-${String(created + 1)}`;
      runVerdict.set(runId, verdicts[created] ?? "passed");
      runCriteria.set(runId, criteria[created] ?? []);
      created += 1;
      reply(201, { run_id: runId, status: "queued", verdict: null });
      return;
    }

    const reportMatch = /^\/api\/v1\/runs\/([^/]+)\/report$/.exec(url);
    if (reportMatch) {
      const runId = reportMatch[1] ?? "";
      reply(200, {
        run_id: runId,
        verdict: runVerdict.get(runId) ?? null,
        plan: { plan_id: "plan-1", plan_version: "1" },
        criteria: (runCriteria.get(runId) ?? []).map((criterion) => ({
          ...criterion,
          failure_kind: criterion.outcome === "not_met" ? "product" : null,
          model_derived: false,
          step_id: `assert-${criterion.criterion_id}`,
        })),
      });
      return;
    }

    const runMatch = /^\/api\/v1\/runs\/([^/]+)$/.exec(url);
    if (runMatch) {
      const runId = runMatch[1] ?? "";
      reply(200, {
        run_id: runId,
        status: "completed",
        verdict: runVerdict.get(runId) ?? "passed",
      });
      return;
    }
    reply(404, { detail: "not found" });
  });

  await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
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
  };
}

const input = {
  projectId: "p-1",
  planId: "plan-1",
  planVersion: "1",
  count: 3,
  timeoutMsPerRun: 5_000,
};

const silent = (): void => undefined;

describe("counting", () => {
  it.each(["1", "0", "21", "two", "2.5"])("refuses --count %s", (raw) => {
    expect(() => validateCount(raw)).toThrow(CliError);
  });

  it("accepts a sensible count and defaults to three", () => {
    expect(validateCount("5")).toBe(5);
    expect(validateCount(undefined)).toBe(3);
  });
});

describe("replaying", () => {
  it("gives every replay its own idempotency key", async () => {
    // A shared key would return the first run three times and report perfect
    // stability for a plan that ran once.
    const { client, requests } = await stub(["passed", "passed", "passed"]);

    const report = await measureFlakiness(client, input, silent);

    const keys = requests
      .filter((request) => request.method === "POST")
      .map((request) => request.idempotencyKey);
    expect(new Set(keys).size).toBe(3);
    expect(new Set(report.run_ids).size).toBe(3);
  });

  it("calls a plan stable only when every replay agreed", async () => {
    const { client } = await stub(["passed", "passed", "passed"]);

    const report = await measureFlakiness(client, input, silent);

    expect(report.stable).toBe(true);
    expect(report.agreement).toBe(1);
    expect(report.verdicts).toEqual({ passed: 3 });
  });

  it("calls a plan unstable when the verdict moves at all", async () => {
    // Two passes out of three is not "mostly fine"; it is unusable as a gate.
    const { client } = await stub(["passed", "failed", "passed"]);

    const report = await measureFlakiness(client, input, silent);

    expect(report.stable).toBe(false);
    expect(report.agreement).toBeCloseTo(2 / 3);
    expect(report.verdicts).toEqual({ passed: 2, failed: 1 });
  });

  it("names the criterion that flipped, which is what a developer acts on", async () => {
    const { client } = await stub(
      ["passed", "failed", "passed"],
      [
        [
          { criterion_id: "ac-1", outcome: "met" },
          { criterion_id: "ac-2", outcome: "met" },
        ],
        [
          { criterion_id: "ac-1", outcome: "met" },
          { criterion_id: "ac-2", outcome: "not_met" },
        ],
        [
          { criterion_id: "ac-1", outcome: "met" },
          { criterion_id: "ac-2", outcome: "met" },
        ],
      ],
    );

    const report = await measureFlakiness(client, input, silent);

    expect(report.unstable_criteria).toHaveLength(1);
    expect(report.unstable_criteria[0]?.criterion_id).toBe("ac-2");
    expect(report.unstable_criteria[0]?.outcomes).toEqual({ met: 2, not_met: 1 });
    expect(renderFlaky(report)).toContain("ac-2");
  });

  it("is unstable when a criterion flips even if the verdict does not", async () => {
    // The verdict can survive a flipping criterion; the plan is still not repeatable.
    const { client } = await stub(
      ["inconclusive", "inconclusive"],
      [
        [{ criterion_id: "ac-1", outcome: "unverified" }],
        [{ criterion_id: "ac-1", outcome: "met" }],
      ],
    );

    const report = await measureFlakiness(client, { ...input, count: 2 }, silent);

    expect(report.agreement).toBe(1);
    expect(report.stable).toBe(false);
  });
});

describe("honest reporting", () => {
  it("warns when memory could move between replays", async () => {
    // Under a learning memory, a difference between replay 1 and replay 5 could be
    // the product or could be the agent having learned something.
    const { client } = await stub(["passed", "passed"]);

    const report = await measureFlakiness(
      client,
      { ...input, count: 2, memoryPolicy: "normal" },
      silent,
    );

    expect(report.caveats.join(" ")).toContain("may learn between replays");
  });

  it("stays quiet when memory is frozen", async () => {
    const { client } = await stub(["passed", "passed"]);

    const report = await measureFlakiness(
      client,
      { ...input, count: 2, memoryPolicy: "frozen" },
      silent,
    );

    expect(report.caveats).toEqual([]);
  });

  it("reports progress on stderr, one line per replay", async () => {
    const { client } = await stub(["passed", "passed"]);
    const messages: string[] = [];

    await measureFlakiness(client, { ...input, count: 2 }, (message) => messages.push(message));

    expect(messages).toEqual(["replay 1/2", "replay 2/2"]);
  });
});
