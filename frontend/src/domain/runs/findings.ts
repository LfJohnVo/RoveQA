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

export type FailureKind = "product" | "plan" | "environment" | "policy";

export interface Finding {
  criterionId: string;
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
    (finding) => finding.outcome === "not_met" && finding.failureKind === "product",
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

export interface RunReport {
  runId: string;
  findings: readonly Finding[];
  artifacts: readonly Artifact[];
  /** The evidence set every artifact belongs to. A bundle that mixed two would be
   * incoherent, so the UI shows the one it actually has. */
  evidenceSetId: string | null;
}
