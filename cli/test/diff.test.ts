/**
 * `run diff`: what changed, matched by criterion rather than by position.
 *
 * The properties worth defending are the ones that make a diff trustworthy enough to
 * read: it does not go noisy when a plan gains a step, it says so when the two runs
 * executed different plans, and it does not report "no change" when the evidence
 * behind an identical outcome got weaker.
 */

import { describe, expect, it } from "vitest";

import { CliError } from "../src/errors.js";
import { diffRuns, parseReport, renderDiff, type CriterionChange } from "../src/commands/diff.js";

interface CriterionInput {
  criterion_id: string;
  outcome: string;
  failure_kind?: string | null;
  model_derived?: boolean;
  step_id?: string | null;
}

function report(
  runId: string,
  verdict: string,
  criteria: CriterionInput[],
  plan: { plan_id: string; plan_version: string } | null = {
    plan_id: "plan-1",
    plan_version: "1",
  },
): Record<string, unknown> {
  return {
    schema_version: "roveqa.run-report.v1",
    run_id: runId,
    verdict,
    plan,
    criteria: criteria.map((criterion) => ({
      criterion_id: criterion.criterion_id,
      outcome: criterion.outcome,
      failure_kind: criterion.failure_kind ?? null,
      model_derived: criterion.model_derived ?? false,
      step_id: criterion.step_id ?? `assert-${criterion.criterion_id}`,
      deterministic_observation: null,
      root_cause_hypothesis: null,
      evidence_refs: [],
    })),
  };
}

function changeOf(diff: ReturnType<typeof diffRuns>, criterionId: string): CriterionChange {
  const entry = diff.criteria.find((candidate) => candidate.criterion_id === criterionId);
  if (entry === undefined) throw new Error(`no delta for ${criterionId}`);
  return entry.change;
}

function diff(
  a: Record<string, unknown>,
  b: Record<string, unknown>,
): ReturnType<typeof diffRuns> {
  return diffRuns(parseReport(a, "run-a"), parseReport(b, "run-b"));
}

describe("criterion deltas", () => {
  it("reports a criterion that started passing", () => {
    const result = diff(
      report("run-a", "failed", [{ criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" }]),
      report("run-b", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
    );

    expect(changeOf(result, "ac-1")).toBe("fixed");
    expect(result.verdict_changed).toBe(true);
  });

  it("reports a criterion that started failing", () => {
    const result = diff(
      report("run-a", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
      report("run-b", "failed", [
        { criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" },
      ]),
    );

    expect(changeOf(result, "ac-1")).toBe("broken");
  });

  it("distinguishes a persistent failure from a new one", () => {
    const result = diff(
      report("run-a", "failed", [
        { criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" },
      ]),
      report("run-b", "failed", [
        { criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" },
      ]),
    );

    expect(changeOf(result, "ac-1")).toBe("still_failing");
    expect(result.verdict_changed).toBe(false);
  });

  it("matches criteria by id, not by position", () => {
    // A plan that gained a step in the middle must not make every later criterion
    // look changed — that is the noise that makes a diff worth ignoring.
    const result = diff(
      report("run-a", "passed", [
        { criterion_id: "ac-1", outcome: "met" },
        { criterion_id: "ac-3", outcome: "met" },
      ]),
      report("run-b", "passed", [
        { criterion_id: "ac-1", outcome: "met" },
        { criterion_id: "ac-2", outcome: "met" },
        { criterion_id: "ac-3", outcome: "met" },
      ]),
    );

    expect(changeOf(result, "ac-1")).toBe("unchanged");
    expect(changeOf(result, "ac-3")).toBe("unchanged");
    expect(changeOf(result, "ac-2")).toBe("added");
    expect(result.changed_count).toBe(1);
  });

  it("reports a criterion the newer plan dropped", () => {
    const result = diff(
      report("run-a", "passed", [
        { criterion_id: "ac-1", outcome: "met" },
        { criterion_id: "ac-2", outcome: "met" },
      ]),
      report("run-b", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
    );

    expect(changeOf(result, "ac-2")).toBe("removed");
  });

  it("reports a criterion nobody could verify any more", () => {
    const result = diff(
      report("run-a", "failed", [
        { criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" },
      ]),
      report("run-b", "inconclusive", [{ criterion_id: "ac-1", outcome: "unverified" }]),
    );

    expect(changeOf(result, "ac-1")).toBe("now_unverified");
  });
});

describe("evidence quality", () => {
  it("flags a pass that stopped being reproducible", () => {
    // Both runs say "met". They are not the same claim: the second rests on a model.
    const result = diff(
      report("run-a", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
      report("run-b", "passed", [
        { criterion_id: "ac-1", outcome: "met", model_derived: true },
      ]),
    );

    expect(changeOf(result, "ac-1")).toBe("weaker_evidence");
    expect(result.changed_count).toBe(1);
  });

  it("flags a pass that became reproducible", () => {
    const result = diff(
      report("run-a", "passed", [
        { criterion_id: "ac-1", outcome: "met", model_derived: true },
      ]),
      report("run-b", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
    );

    expect(changeOf(result, "ac-1")).toBe("stronger_evidence");
  });

  it("reports nothing when two identical runs are compared", () => {
    const identical = report("run-a", "passed", [{ criterion_id: "ac-1", outcome: "met" }]);

    const result = diff(identical, { ...identical, run_id: "run-b" });

    expect(result.changed_count).toBe(0);
    expect(renderDiff(result)).toContain("no criterion changed");
  });
});

describe("plan provenance", () => {
  it("says loudly when the two runs executed different plan versions", () => {
    // Everything else in the diff means less when the plans differ.
    const result = diff(
      report("run-a", "passed", [{ criterion_id: "ac-1", outcome: "met" }], {
        plan_id: "plan-1",
        plan_version: "1",
      }),
      report("run-b", "failed", [
        { criterion_id: "ac-1", outcome: "not_met", failure_kind: "product" },
      ], { plan_id: "plan-1", plan_version: "2" }),
    );

    expect(result.plan_changed).toBe(true);
    expect(renderDiff(result)).toContain("answered different questions");
  });

  it("does not claim a plan change when both ran the same version", () => {
    const result = diff(
      report("run-a", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
      report("run-b", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
    );

    expect(result.plan_changed).toBe(false);
    expect(renderDiff(result)).not.toContain("plan changed");
  });

  it("treats a run with no plan as different from one with a plan", () => {
    const result = diff(
      report("run-a", "inconclusive", [], null),
      report("run-b", "passed", [{ criterion_id: "ac-1", outcome: "met" }]),
    );

    expect(result.plan_changed).toBe(true);
  });
});

describe("report validation", () => {
  it("refuses a report that is not an object", () => {
    expect(() => parseReport("nope", "run-a")).toThrow(CliError);
  });

  it("refuses a report with no criteria array", () => {
    expect(() => parseReport({ run_id: "run-a" }, "run-a")).toThrow(/no criteria/);
  });

  it("refuses a criterion with no id", () => {
    expect(() =>
      parseReport({ run_id: "run-a", criteria: [{ outcome: "met" }] }, "run-a"),
    ).toThrow(/no id or outcome/);
  });
});
