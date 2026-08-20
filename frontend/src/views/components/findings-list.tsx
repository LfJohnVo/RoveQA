import type { Finding } from "@domain/runs/findings";

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
    return <p className="notice">This run verified no acceptance criteria.</p>;
  }

  return (
    <ul className="card-list">
      {findings.map((finding) => (
        <li className="card" key={finding.criterionId}>
          <div className="finding__head">
            <span className="card__name">{finding.criterionId}</span>
            <span className={`badge badge--${toneFor(finding)}`} data-tone={toneFor(finding)}>
              {OUTCOME_LABEL[finding.outcome]}
            </span>
            {finding.failureKind !== null ? (
              <span className="card__meta">{finding.failureKind}</span>
            ) : null}
          </div>

          {finding.deterministicObservation !== null ? (
            <p className="finding__observed">{finding.deterministicObservation}</p>
          ) : null}

          {finding.rootCauseHypothesis !== null ? (
            <p className="finding__hypothesis">
              <span className="finding__label">
                hypothesis{finding.modelName === null ? "" : ` · ${finding.modelName}`}
              </span>{" "}
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
