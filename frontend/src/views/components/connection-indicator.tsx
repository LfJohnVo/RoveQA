import type { ConnectionState } from "@domain/runs/connection";

const LABEL: Record<ConnectionState, string> = {
  connecting: "connecting",
  live: "live",
  reconnecting: "reconnecting — showing the last durable state",
  // A finished run reaches this state on purpose. "Not watching" would read as a
  // fault; there is simply nothing left to receive.
  closed: "finished — nothing more to receive",
};

/**
 * Whether what is on screen is current.
 *
 * Said out loud rather than implied. A console that looks the same whether it is live
 * or stalled invites someone to act on a picture that stopped updating minutes ago.
 */
export function ConnectionIndicator({ state }: { state: ConnectionState }) {
  return (
    <span className={`connection connection--${state}`} role="status">
      <span className="connection__dot" aria-hidden="true" />
      {LABEL[state]}
    </span>
  );
}
