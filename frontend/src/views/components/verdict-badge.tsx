import { verdictTone, type Verdict, type VerdictTone } from "@domain/runs/run";

import { Badge, type BadgeTone } from "./ui";

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
 * suspicion (docs/00). The mapping lives in the domain; this only picks the paint.
 */
const TONE: Record<VerdictTone, BadgeTone> = {
  "answer-pass": "pass",
  "answer-fail": "fail",
  "no-answer": "unsure",
  stopped: "neutral",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const tone = verdictTone(verdict);
  return (
    <Badge tone={TONE[tone]} dataTone={tone}>
      {LABEL[verdict]}
    </Badge>
  );
}
