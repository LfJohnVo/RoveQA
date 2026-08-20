import { verdictTone, type Verdict } from "@domain/runs/run";

const LABEL: Record<Verdict, string> = {
  passed: "passed",
  failed: "failed",
  blocked: "blocked",
  inconclusive: "inconclusive",
  cancelled: "cancelled",
};

/**
 * A verdict, coloured by what it *means* rather than by pass/not-pass.
 *
 * `inconclusive` and `blocked` say the run could not tell. Rendering them in the
 * failure colour would tell a reader their product is broken when nothing about it was
 * established — and once a report has done that, every later one is read with
 * suspicion (docs/00).
 */
export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const tone = verdictTone(verdict);
  return (
    <span className={`badge badge--${tone}`} data-tone={tone}>
      {LABEL[verdict]}
    </span>
  );
}
