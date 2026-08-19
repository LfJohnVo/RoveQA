/**
 * The HTTP client. The CLI talks to the FastAPI control plane and to nothing else —
 * no database, no Temporal, no browser, no model (`.claude/rules/cli.md`).
 *
 * Three rules shape the retry behaviour:
 *
 * - Only failures that carry no answer are retried: a transport error, a 502/503/504,
 *   a 429. A 409 is a real answer and retrying it just asks the same question again.
 * - A mutation is only retried when it carries an idempotency key, because a retry
 *   without one is how a lost response turns into two runs.
 * - `Retry-After` from the server is honoured but capped here. A server that says
 *   "come back in an hour" must not turn a bounded command into an unbounded one.
 */

import { CliError } from "../errors.js";
import type { ErrorCode } from "../output/envelope.js";

/** A response larger than this is refused rather than buffered (docs/25). */
export const MAX_RESPONSE_BYTES = 8 * 1024 * 1024;
export const MAX_RETRY_AFTER_MS = 10_000;
const DEFAULT_ATTEMPTS = 3;

export interface ApiClientOptions {
  baseUrl: string;
  token: string | null;
  requestId: string;
  timeoutMs: number;
  /** Injected so retry behaviour is testable without real waiting. */
  sleep?: (ms: number) => Promise<void>;
  fetchImpl?: typeof fetch;
}

export interface RequestOptions {
  method: "GET" | "POST";
  path: string;
  body?: unknown;
  idempotencyKey?: string;
  /** Overrides the per-request timeout, e.g. for a bounded long-poll. */
  timeoutMs?: number;
  attempts?: number;
}

export interface ApiResponse {
  status: number;
  body: unknown;
}

export class ApiClient {
  private readonly options: ApiClientOptions;
  private readonly sleep: (ms: number) => Promise<void>;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ApiClientOptions) {
    this.options = options;
    this.sleep = options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async request(request: RequestOptions): Promise<ApiResponse> {
    const url = `${this.options.baseUrl.replace(/\/+$/, "")}${request.path}`;
    const retryable = request.method === "GET" || request.idempotencyKey !== undefined;
    const maxAttempts = request.attempts ?? (retryable ? DEFAULT_ATTEMPTS : 1);

    let lastError: CliError | null = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      let response: Response;
      try {
        response = await this.fetchImpl(url, {
          method: request.method,
          headers: this.headers(request),
          ...(request.body === undefined ? {} : { body: JSON.stringify(request.body) }),
          signal: AbortSignal.timeout(request.timeoutMs ?? this.options.timeoutMs),
        });
      } catch (error) {
        lastError = transportError(url, error);
        if (attempt < maxAttempts) {
          await this.sleep(backoffMs(attempt));
          continue;
        }
        throw lastError;
      }

      if (response.ok) return { status: response.status, body: await readBody(response) };

      const failure = await toCliError(response, url);
      if (attempt < maxAttempts && isRetryableStatus(response.status)) {
        await this.sleep(retryDelayMs(response, attempt));
        lastError = failure;
        continue;
      }
      throw failure;
    }

    /* c8 ignore next */
    throw lastError ?? new CliError("INTERNAL_ERROR", "request loop ended without a result");
  }

  /**
   * Fetch raw bytes, for artifacts.
   *
   * Separate from `request` because an artifact is a screenshot or a trace, and
   * running it through JSON parsing would corrupt it. No retries: a partial download
   * is discarded by the caller, which re-materializes the whole bundle.
   */
  async requestBytes(path: string): Promise<Buffer> {
    const url = `${this.options.baseUrl.replace(/\/+$/, "")}${path}`;
    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        headers: { "X-Request-Id": this.options.requestId, ...this.authHeader() },
        signal: AbortSignal.timeout(this.options.timeoutMs),
      });
    } catch (error) {
      throw transportError(url, error);
    }
    if (!response.ok) throw await toCliError(response, url);

    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.byteLength > MAX_RESPONSE_BYTES) {
      throw new CliError("RESOURCE_UNAVAILABLE", `artifact exceeds ${MAX_RESPONSE_BYTES} bytes`);
    }
    return bytes;
  }

  private authHeader(): Record<string, string> {
    return this.options.token === null ? {} : { Authorization: `Bearer ${this.options.token}` };
  }

  private headers(request: RequestOptions): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      // One id correlates the CLI invocation, the API log line and the run event.
      "X-Request-Id": this.options.requestId,
    };
    if (request.body !== undefined) headers["Content-Type"] = "application/json";
    if (request.idempotencyKey !== undefined) {
      headers["Idempotency-Key"] = request.idempotencyKey;
    }
    return { ...headers, ...this.authHeader() };
  }
}

function isRetryableStatus(status: number): boolean {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

function backoffMs(attempt: number): number {
  return Math.min(200 * 2 ** (attempt - 1), MAX_RETRY_AFTER_MS);
}

function retryDelayMs(response: Response, attempt: number): number {
  const header = response.headers.get("retry-after");
  const seconds = header === null ? Number.NaN : Number(header);
  if (Number.isFinite(seconds) && seconds >= 0) {
    return Math.min(seconds * 1000, MAX_RETRY_AFTER_MS);
  }
  return backoffMs(attempt);
}

const STATUS_CODES: Record<number, ErrorCode> = {
  400: "VALIDATION_ERROR",
  401: "AUTH_REQUIRED",
  403: "FORBIDDEN",
  404: "NOT_FOUND",
  409: "CONFLICT",
  412: "VERSION_MISMATCH",
  422: "VALIDATION_ERROR",
  429: "RATE_LIMITED",
  502: "SERVICE_UNAVAILABLE",
  503: "SERVICE_UNAVAILABLE",
  504: "SERVICE_UNAVAILABLE",
};

async function toCliError(response: Response, url: string): Promise<CliError> {
  const body = await readBody(response).catch(() => null);
  const code = STATUS_CODES[response.status] ?? (response.status >= 500 ? "INTERNAL_ERROR" : "VALIDATION_ERROR");
  const detail = extractDetail(body);
  return new CliError(code, `${response.status} from ${url}${detail ? `: ${detail}` : ""}`, {
    details: { status: response.status, body },
  });
}

function transportError(url: string, error: unknown): CliError {
  const message = error instanceof Error ? error.message : String(error);
  const timedOut = error instanceof Error && error.name === "TimeoutError";
  return new CliError("TRANSPORT_ERROR", `cannot reach ${url}: ${message}`, {
    nextAction: timedOut
      ? "The request exceeded its timeout; raise --request-timeout-ms or check the server."
      : "Check that the API is running and that --api-url points at it.",
  });
}

/**
 * Read and parse, refusing an oversized body.
 *
 * `Content-Length` is a claim, not a guarantee, so the actual bytes are measured too:
 * a server that under-reports would otherwise still fill this process's memory.
 */
async function readBody(response: Response): Promise<unknown> {
  const declared = Number(response.headers.get("content-length") ?? Number.NaN);
  if (Number.isFinite(declared) && declared > MAX_RESPONSE_BYTES) {
    throw new CliError("RESOURCE_UNAVAILABLE", `response exceeds ${MAX_RESPONSE_BYTES} bytes`);
  }
  const text = await response.text();
  if (Buffer.byteLength(text, "utf8") > MAX_RESPONSE_BYTES) {
    throw new CliError("RESOURCE_UNAVAILABLE", `response exceeds ${MAX_RESPONSE_BYTES} bytes`);
  }
  if (text.trim() === "") return null;
  try {
    return JSON.parse(text);
  } catch {
    // A 2xx that is not JSON is not a success an agent can act on.
    throw new CliError("TRANSPORT_ERROR", "the server returned a non-JSON body");
  }
}

function extractDetail(body: unknown): string | null {
  if (body === null || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;
  for (const key of ["message", "detail", "error"]) {
    const value = record[key];
    if (typeof value === "string") return value;
  }
  return null;
}
