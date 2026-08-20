/**
 * Whether what a viewer is looking at is current.
 *
 * A domain concept rather than a transport one. The view has to say "this is not live
 * right now", and it must be able to say that without importing anything that knows a
 * WebSocket exists — otherwise the rule that keeps transport out of views has an
 * exception, and an exception is where the next one goes.
 *
 * `reconnecting` and `closed` are separate on purpose: one is a state to wait through,
 * the other is one the user has to be told about.
 */
export type ConnectionState = "connecting" | "live" | "reconnecting" | "closed";

/** True when the screen is showing the last durable state rather than the live one. */
export function isStale(state: ConnectionState): boolean {
  return state !== "live";
}
