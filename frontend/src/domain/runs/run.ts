/**
 * What a run is, in the browser.
 *
 * Deliberately its own type rather than one generated from the backend. The UI needs
 * different things than the server does — "can I still cancel this?", "is this a
 * terminal answer or the absence of one?" — and questions like those belong to a type
 * the views can reason about, not to a transport shape that changes when a column does.
 *
 * The API's shape is validated at the boundary (`infrastructure/api`), so a contract
 * change surfaces as one loud failure there instead of as `undefined` rendered
 * somewhere three layers up.
 */

export const RUN_STATUSES = [
  "created",
  "queued",
  "running",
  "pausing",
  "paused",
  "cancelling",
  "cancelled",
  "completed",
  "failed",
] as const;

export type RunStatus = (typeof RUN_STATUSES)[number];

export const VERDICTS = ["passed", "failed", "blocked", "inconclusive", "cancelled"] as const;

export type Verdict = (typeof VERDICTS)[number];

export interface Run {
  runId: string;
  projectId: string;
  status: RunStatus;
  /** Absent until the run reaches a terminal status. Never inferred from the status:
   * a completed run can be `failed`, and a failed run is not the same as a run that
   * failed to finish. */
  verdict: Verdict | null;
  planId: string | null;
  planVersion: string | null;
}

const TERMINAL: ReadonlySet<RunStatus> = new Set<RunStatus>([
  "completed",
  "failed",
  "cancelled",
]);

const CANCELLABLE: ReadonlySet<RunStatus> = new Set<RunStatus>([
  "created",
  "queued",
  "running",
  "pausing",
  "paused",
]);

export function isTerminal(run: Run): boolean {
  return TERMINAL.has(run.status);
}

/** Whether the run is still going, and so still worth watching live. */
export function isActive(run: Run): boolean {
  return !isTerminal(run);
}

export function canPause(run: Run): boolean {
  return run.status === "running";
}

export function canResume(run: Run): boolean {
  return run.status === "paused";
}

export function canCancel(run: Run): boolean {
  return CANCELLABLE.has(run.status);
}

/**
 * How a verdict should read to a human.
 *
 * `passed` and `failed` are answers. `inconclusive` and `blocked` are the *absence* of
 * an answer, and showing them in the same visual register as a failure would tell
 * someone the product is broken when what actually happened is that the run could not
 * tell (docs/00).
 */
export type VerdictTone = "answer-pass" | "answer-fail" | "no-answer" | "stopped";

export function verdictTone(verdict: Verdict): VerdictTone {
  switch (verdict) {
    case "passed":
      return "answer-pass";
    case "failed":
      return "answer-fail";
    case "blocked":
    case "inconclusive":
      return "no-answer";
    case "cancelled":
      return "stopped";
  }
}
