/**
 * The timeline's dedupe and ordering.
 *
 * These are the Phase 10 gate "a WebSocket reconnect does not duplicate events on
 * screen", proved where the behaviour lives rather than through a rendered component:
 * if the fold is idempotent, no arrival pattern can produce a duplicate row.
 */

import { describe, expect, it } from "vitest";

import { apply, EMPTY_TIMELINE, latestOfType } from "@domain/runs/timeline";

import { makeEvent } from "./fakes";

describe("a reconnect cannot duplicate what is on screen", () => {
  it("drops an event it has already folded in", () => {
    const first = apply(EMPTY_TIMELINE, [makeEvent(1), makeEvent(2)]);

    // Exactly what a reconnect produces: the catch-up overlaps with the live feed.
    const second = apply(first, [makeEvent(2), makeEvent(3)]);

    expect(second.events.map((event) => event.sequence)).toEqual([1, 2, 3]);
  });

  it("applying the same batch twice changes nothing", () => {
    const batch = [makeEvent(1), makeEvent(2)];
    const once = apply(EMPTY_TIMELINE, batch);

    expect(apply(once, batch)).toBe(once);
  });

  it("returns the same timeline for an empty batch", () => {
    const timeline = apply(EMPTY_TIMELINE, [makeEvent(1)]);
    expect(apply(timeline, [])).toBe(timeline);
  });
});

describe("order comes from the durable log, not from arrival", () => {
  it("sorts events that arrive late into place", () => {
    // A slow socket, or a catch-up racing the live feed. Appending in arrival order
    // would render the story of the run out of sequence.
    const timeline = apply(EMPTY_TIMELINE, [makeEvent(3), makeEvent(1), makeEvent(2)]);

    expect(timeline.events.map((event) => event.sequence)).toEqual([1, 2, 3]);
  });

  it("tracks the highest sequence so a reconnect resumes from it", () => {
    const timeline = apply(EMPTY_TIMELINE, [makeEvent(5), makeEvent(2)]);
    expect(timeline.lastSequence).toBe(5);
  });

  it("does not lower the resume point when an older event arrives", () => {
    const timeline = apply(apply(EMPTY_TIMELINE, [makeEvent(9)]), [makeEvent(4)]);
    expect(timeline.lastSequence).toBe(9);
  });
});

describe("latestOfType", () => {
  it("finds the most recent event of a kind", () => {
    const timeline = apply(EMPTY_TIMELINE, [
      makeEvent(1, "run.step"),
      makeEvent(2, "run.status"),
      makeEvent(3, "run.step"),
    ]);

    expect(latestOfType(timeline, "run.step")?.sequence).toBe(3);
  });

  it("returns null rather than guessing when there is none", () => {
    expect(latestOfType(EMPTY_TIMELINE, "run.step")).toBeNull();
  });
});

describe("the socket URL", () => {
  it("targets the realtime router at the root, not under the REST prefix", async () => {
    // Regression: guessing `/api/v1/ws/...` failed silently — a socket that never
    // connected, and a screen stuck on "reconnecting" with no error anyone would see.
    const { WebSocketRunEventStream } = await import("@infrastructure/realtime/run-events");
    const urls: string[] = [];

    const stream = new WebSocketRunEventStream({
      baseUrl: "ws://api.test",
      socketFactory: (url) => {
        urls.push(url);
        return { close: () => undefined } as unknown as WebSocket;
      },
      schedule: () => () => undefined,
    });
    stream.subscribe("run-1", { onEvents: () => undefined, onConnectionChange: () => undefined });

    expect(urls[0]).toBe("ws://api.test/ws/runs/run-1?after=0");
  });
});
