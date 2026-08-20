/**
 * Live run events over WebSocket.
 *
 * The rule that shapes everything here: **the socket makes the durable log timely, it
 * is not the log.** So this adapter never tries to be the source of truth. It
 * reconnects from the last sequence it saw, deliberately overlapping with what the
 * caller already has, because a duplicate is free (the timeline dedupes by sequence)
 * and a gap is not.
 *
 * Reconnection is bounded and jittered. A control plane whose UI hammers a restarting
 * API is a UI that helps keep it down.
 */

import type { RunEventStream, RunSubscription } from "@application/ports/gateways";
import type { ConnectionState } from "@domain/runs/connection";
import type { RunEvent } from "@domain/runs/timeline";

import { toRunEvent } from "../api/schemas";

export const WS_PATH = "/ws/runs";

const FIRST_RETRY_MS = 500;
const MAX_RETRY_MS = 10_000;

export interface RunEventStreamOptions {
  /** Where the socket lives. Defaults to the page's own origin, which is what the dev
   * proxy and the production deployment both serve the API from. */
  baseUrl?: string;
  socketFactory?: (url: string) => WebSocket;
  /** Injected so a test can drive reconnection without waiting real seconds. */
  schedule?: (run: () => void, delayMs: number) => () => void;
  randomFraction?: () => number;
}

export class WebSocketRunEventStream implements RunEventStream {
  private readonly baseUrl: string;
  private readonly socketFactory: (url: string) => WebSocket;
  private readonly schedule: (run: () => void, delayMs: number) => () => void;
  private readonly randomFraction: () => number;

  constructor(options: RunEventStreamOptions = {}) {
    this.baseUrl = options.baseUrl ?? "";
    this.socketFactory = options.socketFactory ?? ((url) => new WebSocket(url));
    this.schedule =
      options.schedule ??
      ((run, delayMs) => {
        const handle = setTimeout(run, delayMs);
        return () => clearTimeout(handle);
      });
    this.randomFraction = options.randomFraction ?? Math.random;
  }

  subscribe(
    runId: string,
    handlers: {
      onEvents: (events: readonly RunEvent[]) => void;
      onConnectionChange: (state: ConnectionState) => void;
    },
  ): RunSubscription {
    let closedByCaller = false;
    let socket: WebSocket | null = null;
    let cancelRetry: (() => void) | null = null;
    let attempt = 0;
    // Resume point. Overlapping by one is intentional: `after` is exclusive on the
    // server, so asking from the last sequence seen returns strictly newer events and
    // never skips one that landed during the handover.
    let lastSequence = 0;

    const connect = (): void => {
      if (closedByCaller) return;
      handlers.onConnectionChange(attempt === 0 ? "connecting" : "reconnecting");

      const url = this.socketUrl(runId, lastSequence);
      const next = this.socketFactory(url);
      socket = next;

      next.onopen = () => {
        attempt = 0;
        handlers.onConnectionChange("live");
      };

      next.onmessage = (message: MessageEvent<unknown>) => {
        const event = parseEvent(message.data);
        if (event === null) return;
        lastSequence = Math.max(lastSequence, event.sequence);
        handlers.onEvents([event]);
      };

      next.onclose = () => {
        if (closedByCaller) {
          handlers.onConnectionChange("closed");
          return;
        }
        attempt += 1;
        handlers.onConnectionChange("reconnecting");
        cancelRetry = this.schedule(connect, this.backoffMs(attempt));
      };

      // An error is always followed by a close, so recovery is handled there. Doing it
      // in both places would open two sockets for one failure.
      next.onerror = () => undefined;
    };

    connect();

    return {
      close: () => {
        closedByCaller = true;
        cancelRetry?.();
        socket?.close();
        handlers.onConnectionChange("closed");
      },
    };
  }

  private socketUrl(runId: string, after: number): string {
    const base = this.baseUrl !== "" ? this.baseUrl : originAsWebSocket();
    // `/ws/runs/...`, not under `/api/v1`: the realtime router is mounted at the root
    // (docs/12). Guessing the REST prefix here failed silently as a socket that would
    // never connect, with the screen stuck on "reconnecting".
    return `${base}${WS_PATH}/${encodeURIComponent(runId)}?after=${after}`;
  }

  /** Exponential with full jitter: a restarting API should not be met by every open
   * tab retrying in lockstep. */
  private backoffMs(attempt: number): number {
    const ceiling = Math.min(MAX_RETRY_MS, FIRST_RETRY_MS * 2 ** (attempt - 1));
    return Math.round(ceiling * (0.5 + 0.5 * this.randomFraction()));
  }
}

function originAsWebSocket(): string {
  const { protocol, host } = globalThis.location;
  return `${protocol === "https:" ? "wss:" : "ws:"}//${host}`;
}

/**
 * A frame that is not a usable event is dropped, not guessed at.
 *
 * The timeline is what a human reads to understand what the agent did; inventing a
 * row from a malformed frame would be worse than missing one, and the durable log
 * still has the real thing for the next catch-up.
 */
function parseEvent(data: unknown): RunEvent | null {
  if (typeof data !== "string") return null;
  try {
    return toRunEvent(JSON.parse(data));
  } catch {
    return null;
  }
}
