/**
 * `roveqa plan scaffold` and `roveqa plan lint`.
 *
 * Both are entirely local: no API, no credentials, no browser, no model. That is the
 * point of lint — an author fixing a plan should not need a running platform, and a
 * plan that cannot pass schema validation should never consume a run.
 *
 * Lint goes further than the schema, because a plan can be schema-valid and still be
 * a bad plan. The extra checks are the ones the phase's authoring rules name: stable
 * step ids, assertions that trace back to a criterion, and a bounded budget.
 */

import { readFileSync } from "node:fs";

import { CliError } from "../errors.js";
import { validateAgainst } from "../contracts/schemas.js";

/** A plan file bigger than this is not a plan; it is an accident or an attack. */
export const MAX_PLAN_BYTES = 1_000_000;

export interface LintFinding {
  severity: "error" | "warning";
  path: string;
  message: string;
}

interface PlanStep {
  step_id?: unknown;
  type?: unknown;
  description?: unknown;
  criterion_id?: unknown;
}

interface PlanDocument {
  schema_version?: unknown;
  plan_steps?: unknown;
  run_policy_id?: unknown;
  budget?: unknown;
}

export function readPlanFile(path: string): unknown {
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (error) {
    throw new CliError("NOT_FOUND", `cannot read plan file: ${path}`, {
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }
  // Plan files are user input (docs/25): bound the size before parsing, not after.
  if (Buffer.byteLength(raw, "utf8") > MAX_PLAN_BYTES) {
    throw new CliError("VALIDATION_ERROR", `plan file exceeds ${MAX_PLAN_BYTES} bytes: ${path}`);
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new CliError("VALIDATION_ERROR", `plan file is not valid JSON: ${path}`, {
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }
}

export function lintPlan(plan: unknown): LintFinding[] {
  const findings: LintFinding[] = validateAgainst("test-plan", plan).map((problem) => ({
    severity: "error" as const,
    path: problem.path,
    message: problem.message,
  }));

  if (plan === null || typeof plan !== "object" || Array.isArray(plan)) return findings;
  const document = plan as PlanDocument;
  const steps = Array.isArray(document.plan_steps) ? (document.plan_steps as PlanStep[]) : [];

  const seen = new Set<string>();
  steps.forEach((step, index) => {
    const at = `/plan_steps/${index}`;
    const stepId = typeof step.step_id === "string" ? step.step_id : null;

    if (stepId !== null) {
      if (seen.has(stepId)) {
        // Evidence and diffs are keyed by step id; two steps sharing one makes a
        // failure impossible to attribute.
        findings.push({
          severity: "error",
          path: `${at}/step_id`,
          message: `duplicate step_id "${stepId}"`,
        });
      }
      seen.add(stepId);
      if (/^(step|s)[-_]?\d+$/i.test(stepId)) {
        findings.push({
          severity: "warning",
          path: `${at}/step_id`,
          message:
            `positional step_id "${stepId}" is not stable: inserting a step renumbers ` +
            "the evidence of every step after it",
        });
      }
    }

    if (step.type === "assertion" && typeof step.criterion_id !== "string") {
      findings.push({
        severity: "error",
        path: `${at}/criterion_id`,
        message: "an assertion must name the acceptance criterion it verifies",
      });
    }

    if (typeof step.description === "string" && looksLikeSelector(step.description)) {
      findings.push({
        severity: "warning",
        path: `${at}/description`,
        message:
          "the description looks like a CSS/XPath selector; plans describe user " +
          "intent, and a selector breaks on the next redesign",
      });
    }
  });

  if (document.run_policy_id === undefined && document.budget === undefined) {
    findings.push({
      severity: "error",
      path: "/",
      message: "a plan must reference a run_policy_id or carry a bounded budget",
    });
  }

  if (!steps.some((step) => step.type === "assertion")) {
    findings.push({
      severity: "warning",
      path: "/plan_steps",
      message: "no assertion step: this plan can never conclude that anything worked",
    });
  }

  return findings;
}

function looksLikeSelector(description: string): boolean {
  return (
    /^\s*[.#][A-Za-z_-]/.test(description) ||
    /\[(data-testid|id|class)=/.test(description) ||
    description.includes("//div") ||
    description.includes("querySelector")
  );
}

export interface ScaffoldOptions {
  name: string;
  projectId: string;
  runPolicyId?: string | undefined;
}

/** A plan that lints clean, so `scaffold | lint` is a working loop from the start. */
export function scaffoldPlan(options: ScaffoldOptions): Record<string, unknown> {
  return {
    schema_version: "roveqa.test-plan.v1",
    project_id: options.projectId,
    name: options.name,
    mode: "story",
    ...(options.runPolicyId
      ? { run_policy_id: options.runPolicyId }
      : { budget: { max_actions: 40, max_duration_seconds: 600, max_model_calls: 30 } }),
    plan_steps: [
      {
        step_id: "sign-in",
        type: "action",
        description: "Sign in as a returning customer",
      },
      {
        step_id: "assert-signed-in",
        type: "assertion",
        description: "The account menu shows the customer's name",
        criterion_id: "ac-signed-in",
        critical: true,
      },
    ],
  };
}

export function hasErrors(findings: LintFinding[]): boolean {
  return findings.some((finding) => finding.severity === "error");
}
