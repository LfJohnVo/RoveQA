/**
 * Exit codes are part of the public contract (`plans/phase-08-agent-first-cli.md`).
 *
 * A shell script that only sees the number must still be able to act correctly, so
 * the families are distinct: 0 is success *and* a passing verdict, 1 is a run that
 * reached a terminal non-pass verdict, and everything from 2 up is the CLI or the
 * transport failing rather than the product.
 *
 * The distinction that matters most is 1 versus 7: a failing verdict is an answer,
 * while a wait timeout is the absence of one — the run is still going.
 */

import type { ErrorCode } from "./envelope.js";

export const EXIT_OK = 0;
export const EXIT_NON_PASS_VERDICT = 1;

const BY_ERROR_CODE: Record<ErrorCode, number> = {
  USAGE_ERROR: 2,
  CONFIG_ERROR: 2,
  AUTH_REQUIRED: 3,
  FORBIDDEN: 3,
  NOT_FOUND: 4,
  VALIDATION_ERROR: 5,
  CONFLICT: 6,
  VERSION_MISMATCH: 6,
  WAIT_TIMEOUT: 7,
  TRANSPORT_ERROR: 8,
  SERVICE_UNAVAILABLE: 8,
  INTERNAL_ERROR: 9,
  POLICY_DENIED: 10,
  RATE_LIMITED: 11,
  RESOURCE_UNAVAILABLE: 11,
};

export function exitCodeFor(code: ErrorCode): number {
  return BY_ERROR_CODE[code];
}

/** Terminal QA verdicts. `passed` is the only one that exits 0. */
export const TERMINAL_VERDICTS = [
  "passed",
  "failed",
  "blocked",
  "inconclusive",
  "cancelled",
] as const;

export type Verdict = (typeof TERMINAL_VERDICTS)[number];

export function isTerminalVerdict(value: string | null | undefined): value is Verdict {
  return value != null && (TERMINAL_VERDICTS as readonly string[]).includes(value);
}

/**
 * A verdict is a domain value, never inferred from whether the process worked.
 * The CLI succeeded either way; what the code reports is what the run concluded.
 */
export function exitCodeForVerdict(verdict: Verdict): number {
  return verdict === "passed" ? EXIT_OK : EXIT_NON_PASS_VERDICT;
}
