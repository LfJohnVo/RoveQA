/**
 * `roveqa run create|get|wait|cancel`.
 *
 * The lifecycle rule that shapes this file: **waiting is not owning**. `run wait`
 * polls a durable run; when the client's deadline expires or the operator interrupts
 * it, the CLI detaches and says how to resume. It never cancels — a run that stopped
 * because a terminal was closed would be a run nobody can trust to finish.
 *
 * Cancelling is a separate, explicit command, exactly as docs/25 requires.
 */

import { randomUUID } from "node:crypto";

import type { ApiClient } from "../client/api.js";
import { CliError } from "../errors.js";
import { isTerminalVerdict, type Verdict } from "../output/exit-codes.js";

export const DEFAULT_WAIT_TIMEOUT_MS = 300_000;
export const POLL_INTERVAL_MS = 2_000;

export interface RunState {
  run_id: string;
  status: string;
  verdict: string | null;
  plan_id: string | null;
  plan_version: string | null;
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

/**
 * Validate the shape at runtime rather than casting.
 *
 * A 200 with the wrong body is not a success, and a static cast would let a server
 * change break the exit code silently — the CLI would report a verdict of
 * `undefined` as a non-pass and nobody would know why.
 */
export function parseRunState(body: unknown): RunState {
  if (body === null || typeof body !== "object") {
    throw new CliError("TRANSPORT_ERROR", "the server returned a run that is not an object");
  }
  const record = body as Record<string, unknown>;
  const runId = record.run_id;
  const status = record.status;
  if (typeof runId !== "string" || typeof status !== "string") {
    throw new CliError("TRANSPORT_ERROR", "the server returned a run without run_id or status");
  }
  const raw = record.verdict;
  if (raw !== null && raw !== undefined && !(typeof raw === "string" && isTerminalVerdict(raw))) {
    // An unrecognised verdict is not something to pass through: the exit code is
    // derived from it, so an unknown value would silently become "not passed".
    throw new CliError("TRANSPORT_ERROR", `unknown verdict from the server: ${JSON.stringify(raw)}`);
  }
  return {
    run_id: runId,
    status,
    verdict: typeof raw === "string" ? raw : null,
    plan_id: typeof record.plan_id === "string" ? record.plan_id : null,
    plan_version: typeof record.plan_version === "string" ? record.plan_version : null,
  };
}

export interface CreateRunInput {
  projectId: string;
  planId: string;
  planVersion: string;
  environmentId?: string | undefined;
  idempotencyKey?: string | undefined;
}

export async function createRun(client: ApiClient, input: CreateRunInput): Promise<RunState> {
  // The key is generated when the caller does not supply one, so a retry inside this
  // process cannot create a second run. A caller who wants a *new* run passes a new
  // key (or omits it and calls again).
  const idempotencyKey = input.idempotencyKey ?? randomUUID();
  const response = await client.request({
    method: "POST",
    path: "/api/v1/runs",
    idempotencyKey,
    body: {
      project_id: input.projectId,
      plan_id: input.planId,
      plan_version: input.planVersion,
      ...(input.environmentId ? { environment_id: input.environmentId } : {}),
    },
  });
  return parseRunState(response.body);
}

export async function getRun(client: ApiClient, runId: string): Promise<RunState> {
  const response = await client.request({ method: "GET", path: `/api/v1/runs/${encodeURIComponent(runId)}` });
  return parseRunState(response.body);
}

export interface WaitOutcome {
  run: RunState;
  verdict: Verdict | null;
  /** True when the client's deadline expired while the run was still going. */
  timedOut: boolean;
}

export interface WaitOptions {
  timeoutMs?: number;
  pollIntervalMs?: number;
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
  signal?: AbortSignal;
}

/**
 * Poll until the run reaches a terminal status or the client deadline expires.
 *
 * The deadline belongs to the client alone. Nothing here tells the server to stop,
 * which is why a timeout is reported as `WAIT_TIMEOUT` (exit 7) and not as a verdict:
 * there is no answer yet, and pretending otherwise would let CI record a failure for
 * a run that went on to pass.
 */
export async function waitForRun(
  client: ApiClient,
  runId: string,
  options: WaitOptions = {},
): Promise<WaitOutcome> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_WAIT_TIMEOUT_MS;
  const pollIntervalMs = options.pollIntervalMs ?? POLL_INTERVAL_MS;
  const now = options.now ?? Date.now;
  const sleep = options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const deadline = now() + timeoutMs;

  for (;;) {
    const run = await getRun(client, runId);
    if (TERMINAL_STATUSES.has(run.status)) {
      return {
        run,
        verdict: isTerminalVerdict(run.verdict) ? run.verdict : null,
        timedOut: false,
      };
    }
    // Interruption is a detach too: the run keeps going and the caller is told how
    // to pick the wait back up.
    if (options.signal?.aborted === true || now() + pollIntervalMs > deadline) {
      return { run, verdict: null, timedOut: true };
    }
    await sleep(pollIntervalMs);
  }
}

export async function cancelRun(client: ApiClient, runId: string): Promise<void> {
  // Cancellation is explicit and naturally idempotent: signalling an already terminal
  // run is a no-op server-side, so a retry cannot cancel something twice.
  await client.request({
    method: "POST",
    path: `/api/v1/runs/${encodeURIComponent(runId)}/cancel`,
    idempotencyKey: randomUUID(),
  });
}


/** Fetch the coherent failure snapshot the bundle is materialized from. */
export async function failureContext(client: ApiClient, runId: string): Promise<unknown> {
  const response = await client.request({
    method: "GET",
    path: `/api/v1/runs/${encodeURIComponent(runId)}/failure-context`,
  });
  return response.body;
}

export async function rerun(
  client: ApiClient,
  runId: string,
  idempotencyKey?: string,
): Promise<RunState> {
  // A rerun is a mutation, so it carries a key. Deriving the key from the source run
  // id would make a second, deliberate rerun impossible.
  const response = await client.request({
    method: "POST",
    path: `/api/v1/runs/${encodeURIComponent(runId)}/rerun`,
    idempotencyKey: idempotencyKey ?? randomUUID(),
  });
  return parseRunState(response.body);
}
