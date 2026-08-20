/**
 * The ordered story of a run, assembled from durable events.
 *
 * The one rule this file exists for: **a run's timeline is derived from its durable
 * event sequence, never from arrival order.** The same event can arrive twice — REST
 * catch-up and the live socket overlap on purpose so a reconnect cannot leave a hole —
 * and a timeline built by appending whatever showed up would render duplicates and, on
 * a slow socket, render them out of order.
 *
 * Sequence numbers come from the server's durable log, so they are the only ordering
 * the UI can trust.
 */

export interface RunEvent {
  eventId: string;
  sequence: number;
  runId: string;
  type: string;
  occurredAt: string;
  payload: Readonly<Record<string, unknown>>;
}

export interface Timeline {
  readonly events: readonly RunEvent[];
  /** Highest sequence seen. What a reconnect asks the server to continue from. */
  readonly lastSequence: number;
}

export const EMPTY_TIMELINE: Timeline = { events: [], lastSequence: 0 };

/**
 * Fold events into a timeline, dropping ones already seen.
 *
 * Pure and idempotent: applying the same batch twice produces the same timeline. That
 * is what makes "reconnect does not duplicate events" a property of this function
 * rather than a hope about how the socket behaves.
 */
export function apply(timeline: Timeline, incoming: readonly RunEvent[]): Timeline {
  if (incoming.length === 0) return timeline;

  const seen = new Set(timeline.events.map((event) => event.sequence));
  const fresh = incoming.filter((event) => !seen.has(event.sequence));
  if (fresh.length === 0) return timeline;

  const events = [...timeline.events, ...fresh].sort((a, b) => a.sequence - b.sequence);
  return {
    events,
    lastSequence: Math.max(timeline.lastSequence, ...fresh.map((event) => event.sequence)),
  };
}

/** The most recent event of a kind, for the "what is happening now" line. */
export function latestOfType(timeline: Timeline, type: string): RunEvent | null {
  for (let index = timeline.events.length - 1; index >= 0; index -= 1) {
    const event = timeline.events[index];
    if (event !== undefined && event.type === type) return event;
  }
  return null;
}
