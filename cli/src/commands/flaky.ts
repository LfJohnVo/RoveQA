/**
 * `roveqa run flaky <plan-file> --count N` — replay a plan and measure whether it
 * agrees with itself.
 *
 * The question is not "does it pass" but "does it answer the same thing every time".
 * A plan whose runs disagree is unusable as a gate whichever way it lands, so the
 * headline number is agreement, not pass rate.
 *
 * Three decisions shape it:
 *
 * **Memory must not move between replays.** A plan running under `memory_policy:
 * normal` learns between runs, so a difference between replay 1 and replay 5 could be
 * the product, or could be the agent having learned something. Measuring flakiness
 * under a moving memory measures nothing, so anything but `frozen`/`off` is reported
 * as a caveat on the result rather than quietly averaged in.
 *
 * **Replays are sequential.** Concurrent ones contend for browser and model slots and,
 * worse, interact through the target application's own state — two runs creating the
 * same record would make each other fail and call it flakiness.
 *
 * **Each replay is a new run, not a retry.** Every one carries its own idempotency
 * key: reusing a key would return the first run N times and report perfect stability.
 */

import { randomUUID } from "node:crypto";

import type { ApiClient } from "../client/api.js";
import { CliError } from "../errors.js";
import { loadRunSummary, type RunSummary } from "./diff.js";
import { createRun, waitForRun, type RunState } from "./run.js";

export const MIN_REPLAYS = 2;
export const MAX_REPLAYS = 20;

export interface FlakyInput {
  projectId: string;
  planId: string;
  planVersion: string;
  count: number;
  timeoutMsPerRun: number;
  environmentId?: string | undefined;
  /** From the plan document, so the report can say what memory did between replays. */
  memoryPolicy?: string | undefined;
}

export interface CriterionStability {
  criterion_id: string;
  outcomes: Record<string, number>;
  stable: boolean;
}

export interface FlakyReport {
  plan_id: string;
  plan_version: string;
  requested: number;
  completed: number;
  run_ids: string[];
  verdicts: Record<string, number>;
  /** Fraction of completed replays that reached the most common verdict. */
  agreement: number;
  stable: boolean;
  unstable_criteria: CriterionStability[];
  caveats: string[];
}

export function validateCount(raw: string | undefined): number {
  const count = raw === undefined ? 3 : Number(raw);
  if (!Number.isInteger(count) || count < MIN_REPLAYS || count > MAX_REPLAYS) {
    throw new CliError(
      "USAGE_ERROR",
      `--count must be an integer between ${MIN_REPLAYS} and ${MAX_REPLAYS}`,
      {
        nextAction:
          "One replay cannot disagree with anything, and a hundred is an afternoon.",
      },
    );
  }
  return count;
}

export async function measureFlakiness(
  client: ApiClient,
  input: FlakyInput,
  onProgress: (message: string) => void,
): Promise<FlakyReport> {
  const caveats: string[] = [];
  if (input.memoryPolicy !== undefined && !["frozen", "off"].includes(input.memoryPolicy)) {
    caveats.push(
      `memory_policy is "${input.memoryPolicy}": the agent may learn between replays, ` +
        "so a difference here is not necessarily the product",
    );
  }

  const summaries: RunSummary[] = [];
  const runIds: string[] = [];
  const verdicts: Record<string, number> = {};

  for (let replay = 1; replay <= input.count; replay += 1) {
    onProgress(`replay ${String(replay)}/${String(input.count)}`);
    const created = await createRun(client, {
      projectId: input.projectId,
      planId: input.planId,
      planVersion: input.planVersion,
      environmentId: input.environmentId,
      // A fresh key per replay: reusing one would return the first run every time
      // and report perfect stability for a plan nobody actually ran twice.
      idempotencyKey: randomUUID(),
    });
    runIds.push(created.run_id);

    const outcome = await waitForRun(client, created.run_id, {
      timeoutMs: input.timeoutMsPerRun,
    });
    if (outcome.timedOut) {
      // Counted as a caveat, never as a verdict: the run is still going, and folding
      // "no answer yet" into the distribution would invent one.
      caveats.push(`replay ${String(replay)} (${created.run_id}) did not finish in time`);
      continue;
    }

    record(verdicts, verdictOf(outcome.run));
    summaries.push(await loadRunSummary(client, created.run_id));
  }

  const completed = summaries.length;
  const agreement = completed === 0 ? 0 : Math.max(...Object.values(verdicts)) / completed;
  const unstable = unstableCriteria(summaries);

  return {
    plan_id: input.planId,
    plan_version: input.planVersion,
    requested: input.count,
    completed,
    run_ids: runIds,
    verdicts,
    agreement,
    // Stable means every replay agreed, on the verdict and on each criterion. A plan
    // that passes four times out of five is not "80% good"; it is unusable as a gate.
    stable: completed === input.count && agreement === 1 && unstable.length === 0,
    unstable_criteria: unstable,
    caveats,
  };
}

function verdictOf(run: RunState): string {
  return run.verdict ?? "unknown";
}

function record(counts: Record<string, number>, key: string): void {
  counts[key] = (counts[key] ?? 0) + 1;
}

/**
 * Which criteria disagreed across replays.
 *
 * This is what a developer acts on: a verdict that flips tells you something is
 * wrong, and the criterion that flipped tells you where.
 */
function unstableCriteria(summaries: RunSummary[]): CriterionStability[] {
  const byCriterion = new Map<string, Record<string, number>>();
  for (const summary of summaries) {
    for (const [criterionId, side] of summary.criteria) {
      const outcomes = byCriterion.get(criterionId) ?? {};
      record(outcomes, side.outcome);
      byCriterion.set(criterionId, outcomes);
    }
  }

  return [...byCriterion.entries()]
    .map(([criterion_id, outcomes]) => ({
      criterion_id,
      outcomes,
      stable: Object.keys(outcomes).length === 1,
    }))
    .filter((entry) => !entry.stable)
    .sort((left, right) => left.criterion_id.localeCompare(right.criterion_id));
}

export function renderFlaky(report: FlakyReport): string {
  const lines = [
    `plan ${report.plan_id}@${report.plan_version}`,
    `${String(report.completed)}/${String(report.requested)} replays finished`,
    `verdicts: ${Object.entries(report.verdicts)
      .map(([verdict, count]) => `${verdict}×${String(count)}`)
      .join(", ")}`,
    `agreement: ${(report.agreement * 100).toFixed(0)}%`,
    report.stable ? "stable" : "UNSTABLE",
  ];
  for (const criterion of report.unstable_criteria) {
    const spread = Object.entries(criterion.outcomes)
      .map(([outcome, count]) => `${outcome}×${String(count)}`)
      .join(", ");
    lines.push(`  ${criterion.criterion_id}: ${spread}`);
  }
  for (const caveat of report.caveats) lines.push(`  caveat: ${caveat}`);
  return `${lines.join("\n")}\n`;
}
