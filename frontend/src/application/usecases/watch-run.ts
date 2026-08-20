/**
 * Watching a run: durable baseline first, live events second.
 *
 * The order is the recovery property, not a preference. REST is asked first so a page
 * reload rebuilds the whole run from the durable log; the socket only adds what
 * happens next. Subscribing first and backfilling afterwards would leave a hole
 * whenever an event landed between the two calls.
 *
 * A finished run is never subscribed to. It has nothing left to say, and a socket that
 * keeps retrying against it would show "reconnecting" forever on a screen that is
 * simply history.
 *
 * No React here. This is the logic that decides what a run *is* on screen, and it has
 * to be testable without rendering anything.
 */

import type { RunEventStream, RunGateway } from "@application/ports/gateways";
import type { ConnectionState } from "@domain/runs/connection";
import { isTerminal, type Run } from "@domain/runs/run";
import { apply, EMPTY_TIMELINE, type RunEvent, type Timeline } from "@domain/runs/timeline";

export interface RunSnapshot {
  run: Run;
  timeline: Timeline;
  connection: ConnectionState;
}

export interface WatchHandlers {
  onSnapshot: (snapshot: RunSnapshot) => void;
  onError: (error: unknown) => void;
}

export interface RunWatch {
  stop(): void;
}

const STATUS_CHANGED = "run.status.changed";

export function watchRun(
  runId: string,
  gateways: { runs: RunGateway; events: RunEventStream },
  handlers: WatchHandlers,
): RunWatch {
  let stopped = false;
  let timeline: Timeline = EMPTY_TIMELINE;
  let run: Run | null = null;
  let connection: ConnectionState = "connecting";
  let subscription: { close(): void } | null = null;

  const publish = (): void => {
    if (stopped || run === null) return;
    handlers.onSnapshot({ run, timeline, connection });
  };

  const finish = (): void => {
    // Closed, not "reconnecting": there is nothing more to receive, and a screen that
    // says otherwise reads as a broken connection rather than a completed run.
    subscription?.close();
    subscription = null;
    connection = "closed";
  };

  /**
   * A status event says something changed; the durable resource says what it is now.
   *
   * Re-reading rather than trusting the payload keeps one answer to "what status is
   * this run", and it is the same answer a reload would produce. Taking it from the
   * event would make the screen depend on which events happened to arrive.
   */
  const refreshRun = async (): Promise<void> => {
    run = await gateways.runs.get(runId);
    if (isTerminal(run)) finish();
    publish();
  };

  const ingest = (events: readonly RunEvent[]): void => {
    const before = timeline;
    timeline = apply(timeline, events);
    if (timeline === before) return;

    publish();
    if (events.some((event) => event.type === STATUS_CHANGED)) {
      refreshRun().catch((error: unknown) => {
        if (!stopped) handlers.onError(error);
      });
    }
  };

  const begin = async (): Promise<void> => {
    run = await gateways.runs.get(runId);
    timeline = apply(timeline, await gateways.runs.events(runId, 0));

    if (isTerminal(run)) {
      connection = "closed";
      publish();
      return;
    }

    publish();
    if (stopped) return;

    subscription = gateways.events.subscribe(runId, {
      onEvents: ingest,
      onConnectionChange: (state) => {
        // A late connection notice must not undo `closed`: the run finished, and the
        // socket shutting down afterwards is expected rather than a state change.
        if (connection === "closed") return;
        connection = state;
        publish();
      },
    });
  };

  begin().catch((error: unknown) => {
    if (!stopped) handlers.onError(error);
  });

  return {
    stop: () => {
      stopped = true;
      subscription?.close();
      subscription = null;
    },
  };
}
