/**
 * `roveqa run diff <run-a> <run-b>` — what actually changed between two runs.
 *
 * Entirely deterministic, and entirely client-side: both runs already published a
 * report built from durable rows, so a diff is a reading of two existing resources
 * rather than new server state. Nothing here asks a model anything (the phase's rule
 * is deterministic deltas *before* any semantic summary, and v1 has no summary).
 *
 * Two decisions shape the output:
 *
 * **Criteria are matched by `criterion_id`, never by position.** A plan that gained a
 * step in the middle would otherwise show every later criterion as changed, which is
 * exactly the noise that makes a diff worth ignoring.
 *
 * **A drop in evidence quality is a change even when the outcome is identical.** A
 * criterion that passed a deterministic check in run A and passed a model's judgement
 * in run B says "met" both times and is not the same claim. A diff that reported "no
 * change" there would hide the thing most worth knowing.
 */

import type { ApiClient } from "../client/api.js";
import { CliError } from "../errors.js";

export type CriterionChange =
  | "unchanged"
  | "fixed"
  | "broken"
  | "still_failing"
  | "now_unverified"
  | "added"
  | "removed"
  | "weaker_evidence"
  | "stronger_evidence";

export interface CriterionSide {
  outcome: string;
  failure_kind: string | null;
  model_derived: boolean;
  step_id: string | null;
}

export interface CriterionDelta {
  criterion_id: string;
  change: CriterionChange;
  before: CriterionSide | null;
  after: CriterionSide | null;
}

export interface RunSummary {
  run_id: string;
  verdict: string | null;
  plan_id: string | null;
  plan_version: string | null;
  criteria: Map<string, CriterionSide>;
}

export interface RunDiff {
  before: Omit<RunSummary, "criteria">;
  after: Omit<RunSummary, "criteria">;
  verdict_changed: boolean;
  /** True when the two runs executed different plan versions. */
  plan_changed: boolean;
  criteria: CriterionDelta[];
  /** Deltas worth acting on: everything except `unchanged`. */
  changed_count: number;
}

const MET = "met";
const NOT_MET = "not_met";
const UNVERIFIED = "unverified";

export async function loadRunSummary(client: ApiClient, runId: string): Promise<RunSummary> {
  const response = await client.request({
    method: "GET",
    path: `/api/v1/runs/${encodeURIComponent(runId)}/report`,
  });
  return parseReport(response.body, runId);
}

/** Validated at runtime: a report with the wrong shape is not a diff we can trust. */
export function parseReport(body: unknown, runId: string): RunSummary {
  if (body === null || typeof body !== "object") {
    throw new CliError("TRANSPORT_ERROR", `the report for ${runId} is not an object`);
  }
  const record = body as Record<string, unknown>;
  const plan = (record.plan ?? null) as Record<string, unknown> | null;
  const rawCriteria = record.criteria;
  if (!Array.isArray(rawCriteria)) {
    throw new CliError("TRANSPORT_ERROR", `the report for ${runId} has no criteria`);
  }

  const criteria = new Map<string, CriterionSide>();
  for (const entry of rawCriteria) {
    if (entry === null || typeof entry !== "object") continue;
    const criterion = entry as Record<string, unknown>;
    const id = criterion.criterion_id;
    const outcome = criterion.outcome;
    if (typeof id !== "string" || typeof outcome !== "string") {
      throw new CliError("TRANSPORT_ERROR", `a criterion in ${runId} has no id or outcome`);
    }
    criteria.set(id, {
      outcome,
      failure_kind: typeof criterion.failure_kind === "string" ? criterion.failure_kind : null,
      model_derived: criterion.model_derived === true,
      step_id: typeof criterion.step_id === "string" ? criterion.step_id : null,
    });
  }

  return {
    run_id: typeof record.run_id === "string" ? record.run_id : runId,
    verdict: typeof record.verdict === "string" ? record.verdict : null,
    plan_id: typeof plan?.plan_id === "string" ? plan.plan_id : null,
    plan_version: typeof plan?.plan_version === "string" ? plan.plan_version : null,
    criteria,
  };
}

export function diffRuns(before: RunSummary, after: RunSummary): RunDiff {
  const ids = [...new Set([...before.criteria.keys(), ...after.criteria.keys()])].sort();
  const criteria = ids.map((criterion_id) =>
    delta(criterion_id, before.criteria.get(criterion_id), after.criteria.get(criterion_id)),
  );

  return {
    before: summaryOf(before),
    after: summaryOf(after),
    verdict_changed: before.verdict !== after.verdict,
    // Two runs of different plan versions answer different questions. Saying so is
    // the point; comparing them silently is what makes a diff misleading.
    plan_changed:
      before.plan_id !== after.plan_id || before.plan_version !== after.plan_version,
    criteria,
    changed_count: criteria.filter((entry) => entry.change !== "unchanged").length,
  };
}

function summaryOf(run: RunSummary): Omit<RunSummary, "criteria"> {
  return {
    run_id: run.run_id,
    verdict: run.verdict,
    plan_id: run.plan_id,
    plan_version: run.plan_version,
  };
}

function delta(
  criterionId: string,
  before: CriterionSide | undefined,
  after: CriterionSide | undefined,
): CriterionDelta {
  if (before === undefined && after !== undefined) {
    return { criterion_id: criterionId, change: "added", before: null, after };
  }
  if (before !== undefined && after === undefined) {
    return { criterion_id: criterionId, change: "removed", before, after: null };
  }
  /* c8 ignore next */
  if (before === undefined || after === undefined) {
    throw new CliError("INTERNAL_ERROR", `criterion ${criterionId} appears in neither run`);
  }

  return {
    criterion_id: criterionId,
    change: classify(before, after),
    before,
    after,
  };
}

function classify(before: CriterionSide, after: CriterionSide): CriterionChange {
  if (before.outcome !== after.outcome) {
    if (after.outcome === MET) return "fixed";
    if (before.outcome === MET) return "broken";
    if (after.outcome === UNVERIFIED) return "now_unverified";
    return "still_failing";
  }
  if (after.outcome === NOT_MET) return "still_failing";

  // Same outcome. Whether anyone can reproduce it is still allowed to have changed:
  // a deterministic pass replaced by a model's opinion is a weaker claim wearing the
  // same word.
  if (before.model_derived !== after.model_derived) {
    return after.model_derived ? "weaker_evidence" : "stronger_evidence";
  }
  return "unchanged";
}

const MARKS: Record<CriterionChange, string> = {
  unchanged: "  ",
  fixed: "+ ",
  broken: "- ",
  still_failing: "! ",
  now_unverified: "? ",
  added: "> ",
  removed: "< ",
  weaker_evidence: "~ ",
  stronger_evidence: "~ ",
};

export function renderDiff(diff: RunDiff): string {
  const lines = [
    `${diff.before.run_id} ${diff.before.verdict ?? "pending"}`,
    `${diff.after.run_id} ${diff.after.verdict ?? "pending"}`,
  ];
  if (diff.plan_changed) {
    // Loud, because everything below it means less when the plans differ.
    lines.push(
      `plan changed: ${describePlan(diff.before)} -> ${describePlan(diff.after)}; ` +
        "these runs answered different questions",
    );
  }
  lines.push("");
  for (const entry of diff.criteria) {
    if (entry.change === "unchanged") continue;
    lines.push(`${MARKS[entry.change]}${entry.criterion_id}: ${entry.change}`);
  }
  if (diff.changed_count === 0) lines.push("no criterion changed");
  return `${lines.join("\n")}\n`;
}

function describePlan(side: Omit<RunSummary, "criteria">): string {
  return side.plan_id === null ? "none" : `${side.plan_id}@${side.plan_version ?? "?"}`;
}
