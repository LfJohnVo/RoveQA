/**
 * The machine-facing output contract (`contracts/cli-envelope.schema.json`).
 *
 * One rule governs this file: in JSON mode, stdout carries exactly one parseable
 * value and nothing else. An agent parsing our output has no way to recover from a
 * progress line or a deprecation notice printed alongside the payload, so every
 * diagnostic goes to stderr and the envelope is written once, at the end.
 *
 * That is why `emit` is the only function allowed to touch stdout, and why it
 * refuses to run twice.
 */

export const SCHEMA_VERSION = "roveqa.cli.v1";

/** Error codes the envelope may carry. Mirrors the schema's enum exactly. */
export type ErrorCode =
  | "USAGE_ERROR"
  | "CONFIG_ERROR"
  | "AUTH_REQUIRED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "CONFLICT"
  | "VERSION_MISMATCH"
  | "WAIT_TIMEOUT"
  | "TRANSPORT_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "INTERNAL_ERROR"
  | "POLICY_DENIED"
  | "RATE_LIMITED"
  | "RESOURCE_UNAVAILABLE";

export interface EnvelopeError {
  code: ErrorCode;
  message: string;
  next_action?: string | null;
  details?: Record<string, unknown> | null;
}

export type Envelope =
  | { schema_version: typeof SCHEMA_VERSION; request_id: string; data: unknown }
  | { schema_version: typeof SCHEMA_VERSION; request_id: string; error: EnvelopeError };

export type OutputMode = "json" | "text";

export interface Writer {
  out: (line: string) => void;
  err: (line: string) => void;
}

export const processWriter: Writer = {
  out: (line) => process.stdout.write(line),
  err: (line) => process.stderr.write(line),
};

/** Progress, warnings, debug. Never stdout, in either mode. */
export function diagnostic(writer: Writer, message: string): void {
  writer.err(`${message}\n`);
}

export function successEnvelope(requestId: string, data: unknown): Envelope {
  return { schema_version: SCHEMA_VERSION, request_id: requestId, data };
}

export function errorEnvelope(requestId: string, error: EnvelopeError): Envelope {
  // `details: undefined` would disappear in JSON but still fail an exactOptionalProperty
  // comparison in tests; normalizing here keeps one shape on the wire.
  const normalized: EnvelopeError = {
    code: error.code,
    message: error.message,
    next_action: error.next_action ?? null,
    details: error.details ?? null,
  };
  return { schema_version: SCHEMA_VERSION, request_id: requestId, error: normalized };
}

/**
 * Write the single result of a command.
 *
 * In text mode the caller supplies a human rendering; the envelope is still what
 * an agent gets, so `--output json` and text mode can never disagree about what
 * happened — they render the same value.
 */
export function emit(
  writer: Writer,
  mode: OutputMode,
  envelope: Envelope,
  renderText: (envelope: Envelope) => string,
): void {
  if (emitted) {
    // A second write would produce two JSON values on one stream, which is not
    // parseable. Failing loudly beats emitting something no agent can consume.
    throw new Error("the command tried to emit a second result");
  }
  emitted = true;
  writer.out(mode === "json" ? `${JSON.stringify(envelope)}\n` : renderText(envelope));
}

let emitted = false;

/** Test seam: each spawned process emits once, but a test may drive several commands. */
export function resetEmitted(): void {
  emitted = false;
}
