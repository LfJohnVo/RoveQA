/**
 * One typed error carrying everything the envelope and the exit code need.
 *
 * Commands throw these instead of writing output and calling `process.exit`, so
 * there is exactly one place that decides how a failure is rendered and exactly one
 * place that touches stdout.
 */

import type { ErrorCode } from "./output/envelope.js";

export class CliError extends Error {
  readonly code: ErrorCode;
  readonly nextAction: string | null;
  readonly details: Record<string, unknown> | null;

  constructor(
    code: ErrorCode,
    message: string,
    options: {
      nextAction?: string | undefined;
      details?: Record<string, unknown> | undefined;
    } = {},
  ) {
    super(message);
    this.name = "CliError";
    this.code = code;
    this.nextAction = options.nextAction ?? null;
    this.details = options.details ?? null;
  }
}

export function usage(message: string, nextAction?: string): CliError {
  return new CliError("USAGE_ERROR", message, { nextAction });
}

/**
 * Anything that escaped without being classified. Its message is included because a
 * silent "internal error" tells an operator nothing, but the stack is not: it would
 * leak paths into machine output that agents may forward.
 */
export function unclassified(error: unknown): CliError {
  const message = error instanceof Error ? error.message : String(error);
  return new CliError("INTERNAL_ERROR", message);
}
