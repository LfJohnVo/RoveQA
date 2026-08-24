/**
 * The report the console reads, against every failure kind the server can send.
 *
 * This existed as a four-value union while the server had eight and the published
 * contract listed seven. A run blocked on `model` — the ordinary outcome when a small
 * planner produces something unusable — came back from the API with its criterion and
 * its explanation, and the console showed "This run verified no acceptance criteria".
 * The finding, the reason and the evidence were all there and none of them reached the
 * screen. It had been that way since Phase 13.
 */

import { describe, expect, it } from "vitest";

import { toRunReport } from "../src/infrastructure/api/schemas";
import { defects } from "../src/domain/runs/findings";

const KINDS = [
  "product",
  "plan",
  "environment",
  "policy",
  "agent_budget",
  "model",
  "session",
  "unknown",
] as const;

function reportWith(failureKind: string | null): unknown {
  return {
    run_id: "run-1",
    criteria: [
      {
        criterion_id: "ac-1",
        source: "plan",
        outcome: "not_met",
        failure_kind: failureKind,
        deterministic_observation: "the page did not say it",
        model_derived: false,
      },
    ],
    observed_failures: [],
  };
}

const NO_CONTEXT = { run_id: "run-1", evidence_set_id: null, artifacts: [] };

describe("every failure kind the server can send", () => {
  it.each(KINDS)("survives the trip for %s", (kind) => {
    const report = toRunReport(reportWith(kind), NO_CONTEXT);

    expect(report.findings).toHaveLength(1);
    expect(report.findings[0]?.failureKind).toBe(kind);
  });

  it("survives a kind this client has never heard of", () => {
    // The set is the server's to grow. A client that must be edited every time it does
    // is out of date between the two edits, silently — which is exactly what happened.
    const report = toRunReport(reportWith("something_new"), NO_CONTEXT);

    expect(report.findings[0]?.failureKind).toBe("something_new");
  });

  it("still accuses the product for exactly one of them", () => {
    // Widening the type must not widen what counts as a defect.
    for (const kind of KINDS) {
      const report = toRunReport(reportWith(kind), NO_CONTEXT);
      expect(defects(report.findings)).toHaveLength(kind === "product" ? 1 : 0);
    }
  });
});
