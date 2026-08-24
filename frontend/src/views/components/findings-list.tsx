import type { Finding } from "@domain/runs/findings";

import { Badge, type BadgeTone } from "./ui";

const OUTCOME_LABEL: Record<Finding["outcome"], string> = {
  met: "met",
  not_met: "not met",
  unverified: "unverified",
};

/**
 * What each criterion concluded.
 *
 * A deterministic observation and a model's hypothesis are rendered differently and
 * labelled differently. Showing them the same way would let a guess read as a finding
 * about the product — the one mistake that makes every later report suspect (docs/25).
 */
export function FindingsList({ findings }: { findings: readonly Finding[] }) {
  if (findings.length === 0) {
    return (
      <p className="rounded-lg bg-white px-4 py-3 text-sm text-gray-600 shadow-xs dark:bg-gray-800 dark:text-gray-400">
        This run verified no acceptance criteria.
      </p>
    );
  }

  return (
    <ul className="grid gap-4">
      {findings.map((finding) => (
        <li
          className="min-w-0 rounded-lg bg-white p-4 shadow-xs dark:bg-gray-800"
          key={finding.criterionId}
        >
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">
              {finding.criterionId}
            </span>
            {/* Said on the row. A reader must never take "every run checks this page"
                for "the story asked for this", and the two sit in one list. */}
            <span className="text-xs text-gray-500 dark:text-gray-500">
              {finding.source === "sweep" ? "page check" : "from the story"}
            </span>
            <Badge tone={badgeFor(finding)} dataTone={toneFor(finding)}>
              {OUTCOME_LABEL[finding.outcome]}
            </Badge>
            {finding.failureKind !== null ? (
              <span className="text-xs text-gray-500 dark:text-gray-500">
                {finding.failureKind}
              </span>
            ) : null}
          </div>

          {finding.deterministicObservation !== null ? (
            <p className="mt-3 text-sm text-gray-700 dark:text-gray-300">
              {finding.deterministicObservation}
            </p>
          ) : null}

          {finding.rootCauseHypothesis !== null ? (
            // Set apart on purpose: a dashed rule and a label, so a guess can never be
            // skimmed as an observation. The style is doing an editorial job here.
            <p className="mt-3 border-l-2 border-dashed border-gray-300 pl-3 text-sm text-gray-600 dark:border-gray-600 dark:text-gray-400">
              <span className="mr-2 text-xs font-semibold tracking-wide text-yellow-600 uppercase dark:text-yellow-400">
                hypothesis{finding.modelName === null ? "" : ` · ${finding.modelName}`}
              </span>
              {finding.rootCauseHypothesis}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function toneFor(finding: Finding): string {
  if (finding.outcome === "met") return "answer-pass";
  // Only a product failure is an answer about the product. Anything else is the run
  // failing to establish one, and colouring it as a defect would be a lie.
  if (finding.outcome === "not_met") {
    return finding.failureKind === "product" ? "answer-fail" : "no-answer";
  }
  return "no-answer";
}

function badgeFor(finding: Finding): BadgeTone {
  const tone = toneFor(finding);
  if (tone === "answer-pass") return "pass";
  if (tone === "answer-fail") return "fail";
  return "unsure";
}
