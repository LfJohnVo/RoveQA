/**
 * What a run concluded about each acceptance criterion.
 *
 * The separation the whole product rests on, carried into the UI: a deterministic
 * observation is reproducible, a model hypothesis is not, and only the first may
 * accuse the product (docs/00, docs/25). They arrive from the API in two distinct
 * fields, and this type keeps them distinct rather than flattening both into a
 * "message" that a component would render identically.
 */

export type CriterionOutcome = "met" | "not_met" | "unverified";

export const PRODUCT_DEFECT = "product";
/**
 * The only failure kind with meaning in this layer: the one that accuses the product.
 *
 * Everything else is a label the report shows and the UI does not branch on, which is
 * why `FailureKind` is a plain string rather than a union. It used to be a union of four
 * values, and the server had eight — `agent_budget`, `model` and `session` among them —
 * so a blocked run's report failed to parse and the console reported "this run verified
 * no acceptance criteria" about a run that had verified one and explained itself. The
 * published contract had listed the extra kinds since Phase 13; only this copy had not.
 *
 * A union here buys nothing and costs that: the set is the server's to grow, and a
 * client that must be edited every time it does will be out of date between the two
 * edits, silently.
 */
export type FailureKind = string;

/** Who asked for this criterion: the run's plan, or the sweep every run performs. */
export type FindingSource = "plan" | "sweep";

export interface Finding {
  criterionId: string;
  source: FindingSource;
  stepId: string | null;
  outcome: CriterionOutcome;
  failureKind: FailureKind | null;
  /** Reproducible. Present only when a deterministic check produced the answer. */
  deterministicObservation: string | null;
  /** A model's reading. Never presented as an observation. */
  rootCauseHypothesis: string | null;
  modelDerived: boolean;
  modelName: string | null;
}

/**
 * Findings that accuse the product.
 *
 * Only `product` counts. A plan that could not be verified, an environment that was
 * down, or an action the policy refused are all real failures of the *run* — calling
 * any of them a defect is how a report loses the reader's trust.
 */
export function defects(findings: readonly Finding[]): Finding[] {
  return findings.filter(
    (finding) => finding.outcome === "not_met" && finding.failureKind === PRODUCT_DEFECT,
  );
}

/** Criteria nobody could settle. Worth showing, never worth counting as a pass. */
export function unresolved(findings: readonly Finding[]): Finding[] {
  return findings.filter((finding) => finding.outcome === "unverified");
}

export interface Artifact {
  artifactId: string;
  kind: string;
  relativePath: string;
  sha256: string;
  sizeBytes: number;
  stepId: string | null;
}

/**
 * Something the browser saw go wrong that answers no acceptance criterion.
 *
 * Kept apart from `Finding` in the type, not just on screen. A finding is an answer to
 * a question the plan asked and can accuse the application; an observation is neither,
 * and a shape that could hold both would eventually be rendered as both.
 */
export interface ObservedFailure {
  kind: "console_error" | "failed_request";
  detail: string;
  episodeIndex: number;
}

export interface RunReport {
  runId: string;
  findings: readonly Finding[];
  observed: readonly ObservedFailure[];
  artifacts: readonly Artifact[];
  /** The evidence set every artifact belongs to. A bundle that mixed two would be
   * incoherent, so the UI shows the one it actually has. */
  evidenceSetId: string | null;
}
