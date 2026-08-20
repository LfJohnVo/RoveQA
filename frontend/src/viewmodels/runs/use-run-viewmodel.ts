/**
 * The run screen's ViewModel.
 *
 * The surface docs/04 specifies: state the view renders, and commands it invokes. No
 * endpoint, no event name, no transport concept crosses this boundary — a view asks
 * `pause()` and reads `canPause`, and could not construct an HTTP request if it wanted
 * to.
 *
 * Commands are optimistic about *intent*, never about *outcome*: `pause()` marks the
 * command in flight, and the status only changes when the durable log says it did.
 * Showing "paused" because a button was pressed would be the UI inventing a state the
 * server has not reached, which for a control plane is the one lie that matters.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { watchRun, type RunSnapshot } from "@application/usecases/watch-run";
import type { ConnectionState } from "@domain/runs/connection";
import {
  canCancel,
  canPause,
  canResume,
  isTerminal,
  type Run,
  type Verdict,
} from "@domain/runs/run";
import { EMPTY_TIMELINE, type RunEvent, type Timeline } from "@domain/runs/timeline";
import { useGateways } from "@viewmodels/gateways-context";

export type CommandName = "pause" | "resume" | "cancel";

export interface RunViewModel {
  runId: string;
  status: Run["status"] | "loading";
  verdict: Verdict | null;
  isTerminal: boolean;
  timeline: Timeline;
  events: readonly RunEvent[];
  stepCount: number;
  connection: ConnectionState;
  /** True while the live feed is not attached. The view says so rather than showing
   * stale data as if it were current. */
  isStale: boolean;
  error: string | null;
  pending: CommandName | null;
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  pause: () => void;
  resume: () => void;
  cancel: () => void;
}

/** State tagged with the run it belongs to.
 *
 * Navigating to another run makes the previous state stale rather than something to
 * clear: clearing it inside the effect would set state during the effect body, which
 * cascades a render and — for one frame — shows the old run under the new id. */
interface TaggedSnapshot {
  runId: string;
  snapshot: RunSnapshot;
}

interface TaggedError {
  runId: string;
  message: string;
}

export function useRunViewModel(runId: string): RunViewModel {
  const gateways = useGateways();
  const [tagged, setTagged] = useState<TaggedSnapshot | null>(null);
  const [taggedError, setTaggedError] = useState<TaggedError | null>(null);
  const [pending, setPending] = useState<CommandName | null>(null);

  useEffect(() => {
    const watch = watchRun(runId, gateways, {
      onSnapshot: (snapshot) => setTagged({ runId, snapshot }),
      onError: (cause) => setTaggedError({ runId, message: messageFor(cause) }),
    });
    return () => watch.stop();
  }, [runId, gateways]);

  // Anything tagged with a different run is last screen's data, not this one's.
  const snapshot = tagged?.runId === runId ? tagged.snapshot : null;
  const error = taggedError?.runId === runId ? taggedError.message : null;
  const run = snapshot?.run ?? null;

  const send = useCallback(
    (name: CommandName) => {
      setPending(name);
      setTaggedError(null);
      const command = {
        pause: () => gateways.runs.pause(runId),
        resume: () => gateways.runs.resume(runId),
        cancel: () => gateways.runs.cancel(runId),
      }[name];

      command()
        .catch((cause: unknown) => setTaggedError({ runId, message: messageFor(cause) }))
        // Cleared either way: the command was accepted or it failed, and in both cases
        // the durable status is what decides what the buttons do next.
        .finally(() => setPending(null));
    },
    [gateways, runId],
  );

  const pause = useCallback(() => send("pause"), [send]);
  const resume = useCallback(() => send("resume"), [send]);
  const cancel = useCallback(() => send("cancel"), [send]);

  return useMemo(() => {
    const timeline = snapshot?.timeline ?? EMPTY_TIMELINE;
    const connection = snapshot?.connection ?? "connecting";
    const busy = pending !== null;

    return {
      runId,
      status: run?.status ?? "loading",
      verdict: run?.verdict ?? null,
      isTerminal: run !== null && isTerminal(run),
      timeline,
      events: timeline.events,
      stepCount: timeline.events.length,
      connection,
      isStale: connection !== "live" && run !== null && !isTerminal(run),
      error,
      pending,
      // A command already in flight disables the others: two lifecycle commands racing
      // is how a run ends up cancelled by someone who meant to pause it.
      canPause: run !== null && canPause(run) && !busy,
      canResume: run !== null && canResume(run) && !busy,
      canCancel: run !== null && canCancel(run) && !busy,
      pause,
      resume,
      cancel,
    };
  }, [runId, run, snapshot, error, pending, pause, resume, cancel]);
}

function messageFor(cause: unknown): string {
  if (cause instanceof Error) return cause.message;
  return "something went wrong talking to the control plane";
}
