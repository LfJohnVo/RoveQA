/**
 * `roveqa run report` against a stub server.
 *
 * One report, two renderings, and the CLI must not become a third. The markdown comes
 * from the server so there is exactly one place that decides how a report reads — a
 * client-side renderer would be free to drift, and a report that disagrees with itself
 * is worse than one that costs an extra GET.
 *
 * The property that cannot regress: `--output json` still prints one JSON value and
 * nothing else, whatever the markdown looks like.
 */

import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { parseSingleJson, runCli } from "./helpers.js";

const DOCUMENT = {
  schema_version: "roveqa.run-report.v1",
  run_id: "run-1",
  project_id: "proj-1",
  status: "completed",
  verdict: "passed",
  plan: null,
  criteria: [
    {
      criterion_id: "page:/",
      source: "sweep",
      step_id: null,
      outcome: "met",
      failure_kind: null,
      deterministic_observation: "the page answered 200",
      root_cause_hypothesis: null,
      model_derived: false,
      model_invocation_id: null,
      model_name: null,
      prompt_version: null,
      evidence_refs: [],
    },
  ],
  observed_failures: [],
};

const MARKDOWN = "# Run run-1\n\n- Verdict: **passed**\n\n## Observed\n";

let server: Server | undefined;
const accepted: string[] = [];

async function stub(): Promise<string> {
  accepted.length = 0;
  server = createServer((incoming, response) => {
    const accept = incoming.headers.accept ?? "";
    accepted.push(accept);
    incoming.on("data", () => undefined);
    incoming.on("end", () => {
      if (accept.includes("text/markdown")) {
        response.writeHead(200, { "content-type": "text/markdown" });
        response.end(MARKDOWN);
        return;
      }
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify(DOCUMENT));
    });
  });
  await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server?.address() as AddressInfo).port}`;
}

afterEach(async () => {
  // Closed after every test. A stub left listening is a handle vitest waits on, and a
  // suite that hangs at the end looks like a slow test rather than a leak.
  await new Promise<void>((resolve) => {
    if (server === undefined) return resolve();
    server.close(() => resolve());
  });
  server = undefined;
});

describe("run report", () => {
  it("prints one JSON value and nothing else under --output json", async () => {
    const url = await stub();

    const result = await runCli(["run", "report", "run-1", "--api-url", url, "--output", "json"]);

    expect(result.code).toBe(0);
    const envelope = parseSingleJson(result.stdout);
    expect(envelope).toMatchObject({
      schema_version: "roveqa.cli.v1",
      data: { schema_version: "roveqa.run-report.v1", verdict: "passed" },
    });
  });

  it("does not fetch the prose nobody asked for", async () => {
    // The extra GET is the price of one renderer, and it is only worth paying when a
    // person is going to read the result.
    const url = await stub();

    await runCli(["run", "report", "run-1", "--api-url", url, "--output", "json"]);

    expect(accepted.filter((value) => value.includes("text/markdown"))).toEqual([]);
  });

  it("prints the server's markdown under --output text", async () => {
    const url = await stub();

    const result = await runCli(["run", "report", "run-1", "--api-url", url, "--output", "text"]);

    expect(result.code).toBe(0);
    expect(result.stdout).toContain("# Run run-1");
    expect(result.stdout).toContain("Verdict: **passed**");
    // Asked for, rather than the client rendering its own from the document.
    expect(accepted.some((value) => value.includes("text/markdown"))).toBe(true);
  });

  it("reports a missing run rather than printing an empty report", async () => {
    server = createServer((incoming, response) => {
      incoming.on("data", () => undefined);
      incoming.on("end", () => {
        response.writeHead(404, { "content-type": "application/json" });
        response.end(JSON.stringify({ error: { code: "NOT_FOUND", message: "no such run" } }));
      });
    });
    await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
    const url = `http://127.0.0.1:${(server?.address() as AddressInfo).port}`;

    const result = await runCli(["run", "report", "nope", "--api-url", url, "--output", "json"]);

    expect(result.code).toBe(4);
    expect(parseSingleJson(result.stdout)).toMatchObject({ error: { code: "NOT_FOUND" } });
  });
});
