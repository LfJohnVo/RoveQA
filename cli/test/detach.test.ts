/**
 * Interrupting `run wait` detaches; it never cancels.
 *
 * This one has to spawn a real process and send a real SIGINT. The signal handling
 * lives in the entrypoint, and an in-process test would exercise the polling loop
 * while leaving the wiring that actually receives Ctrl-C untested.
 *
 * A stub server stands in for the API and records every request, so the assertion
 * that matters — nothing asked the server to stop — is made on what was sent, not on
 * what the client believes it did.
 */

import { spawn } from "node:child_process";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { CLI_ENTRY, parseSingleJson } from "./helpers.js";

let server: Server | null = null;
afterEach(() => {
  server?.close();
  server = null;
});

interface Recorded {
  method: string;
  url: string;
}

async function neverFinishingRun(): Promise<{ port: number; requests: Recorded[] }> {
  const requests: Recorded[] = [];
  server = createServer((incoming, response) => {
    requests.push({ method: incoming.method ?? "", url: incoming.url ?? "" });
    response.writeHead(200, { "content-type": "application/json" });
    // Always running: the client must be the one that gives up.
    response.end(
      JSON.stringify({ run_id: "run-1", status: "running", verdict: null }),
    );
  });
  await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
  return { port: (server.address() as AddressInfo).port, requests };
}

describe("detaching", () => {
  it("exits 7 when the client deadline expires, and the run is left alone", async () => {
    const { port, requests } = await neverFinishingRun();

    const result = await new Promise<{ code: number; stdout: string }>((resolve, reject) => {
      const child = spawn(
        process.execPath,
        [CLI_ENTRY, "run", "wait", "run-1", "--timeout", "10", "--output", "json"],
        { env: { PATH: process.env.PATH ?? "", ROVEQA_API_URL: `http://127.0.0.1:${port}` } },
      );
      let stdout = "";
      child.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
      child.on("error", reject);
      child.on("close", (code) => resolve({ code: code ?? -1, stdout }));
    });

    expect(result.code).toBe(7);
    const envelope = parseSingleJson(result.stdout);
    const error = envelope.error as { code: string; next_action: string; details: unknown };
    expect(error.code).toBe("WAIT_TIMEOUT");
    // The caller is told how to pick the wait back up, not left guessing.
    expect(error.next_action).toContain("run wait run-1");
    expect((error.details as { status: string }).status).toBe("running");
    expect(requests.every((request) => request.method === "GET")).toBe(true);
  });

  it("detaches on SIGINT without cancelling the run", async () => {
    const { port, requests } = await neverFinishingRun();

    const result = await new Promise<{ code: number; stdout: string; stderr: string }>(
      (resolve, reject) => {
        const child = spawn(
          process.execPath,
          [CLI_ENTRY, "run", "wait", "run-1", "--timeout", "60000", "--output", "json"],
          { env: { PATH: process.env.PATH ?? "", ROVEQA_API_URL: `http://127.0.0.1:${port}` } },
        );
        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
        child.stderr.on("data", (chunk: Buffer) => (stderr += chunk.toString()));
        // Interrupt once the wait is genuinely under way, so this measures the
        // handler rather than a race with startup.
        const interrupt = setInterval(() => {
          if (requests.length > 0) {
            clearInterval(interrupt);
            child.kill("SIGINT");
          }
        }, 20);
        child.on("error", reject);
        child.on("close", (code) => {
          clearInterval(interrupt);
          resolve({ code: code ?? -1, stdout, stderr });
        });
      },
    );

    expect(result.code).toBe(7);
    expect(result.stderr).toContain("detaching");
    expect(parseSingleJson(result.stdout).error).toBeDefined();
    // The assertion the gate is about: nothing was sent to stop the run.
    expect(requests.some((request) => request.url.includes("cancel"))).toBe(false);
    expect(requests.every((request) => request.method === "GET")).toBe(true);
  });
});
