/**
 * Starting a run, once.
 *
 * The idempotency key is minted here — one per user intent — and handed to every
 * attempt of that intent. Generating it inside the gateway would mint a new one per
 * call, so a retry after a lost response would create a second run, which is the whole
 * thing the key exists to prevent (docs/12).
 */

import type { RunGateway, StartRunInput } from "@application/ports/gateways";
import type { Run } from "@domain/runs/run";

export type StartRunRequest = Omit<StartRunInput, "idempotencyKey">;

export interface StartRunAttempt {
  /** Stable across retries of this intent. */
  readonly idempotencyKey: string;
  run(): Promise<Run>;
}

export function prepareRun(
  runs: RunGateway,
  request: StartRunRequest,
  newKey: () => string = () => crypto.randomUUID(),
): StartRunAttempt {
  const idempotencyKey = newKey();
  return {
    idempotencyKey,
    run: () => runs.start({ ...request, idempotencyKey }),
  };
}
