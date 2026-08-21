import type { ConnectionState } from "@domain/runs/connection";

const LABEL: Record<ConnectionState, string> = {
  connecting: "connecting",
  live: "live",
  reconnecting: "reconnecting — showing the last durable state",
  // A finished run reaches this state on purpose. "Not watching" would read as a
  // fault; there is simply nothing left to receive.
  closed: "finished — nothing more to receive",
};

/** The dot's colour is the whole message; the text is for anyone who cannot see it. */
const DOT: Record<ConnectionState, string> = {
  connecting: "bg-yellow-400",
  live: "bg-green-400",
  reconnecting: "bg-yellow-400",
  closed: "bg-gray-400",
};

/**
 * Whether what is on screen is current.
 *
 * Said out loud rather than implied. A console that looks the same whether it is live
 * or stalled invites someone to act on a picture that stopped updating minutes ago.
 */
export function ConnectionIndicator({ state }: { state: ConnectionState }) {
  return (
    <span
      className="inline-flex items-center text-xs font-medium text-gray-600 dark:text-gray-400"
      role="status"
    >
      <span
        className={[
          "mr-2 inline-block h-2 w-2 rounded-full",
          DOT[state],
          // Only a live connection pulses. A steady dot on a finished run is the truth:
          // nothing is arriving, and animating it would suggest otherwise.
          state === "live" ? "motion-safe:animate-pulse" : "",
        ].join(" ")}
        aria-hidden="true"
      />
      {LABEL[state]}
    </span>
  );
}
