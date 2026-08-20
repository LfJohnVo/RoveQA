/**
 * Runtime validation of everything the API returns.
 *
 * TypeScript describes what the server *promised*; these check what it actually sent.
 * The difference matters here more than in most clients: a run's verdict decides what
 * a human is told about their product, and a value the UI does not recognise must
 * surface as an error rather than fall through as "not passed".
 *
 * Parsed into domain types in one step, so nothing above this file ever holds a
 * snake_case transport object.
 */

import { z } from "zod";

import type { MemoryStatus } from "@domain/knowledge/memory";
import type { Artifact, Finding, RunReport } from "@domain/runs/findings";
import type { Project } from "@domain/projects/project";
import type { UserStory } from "@domain/qa/story";
import { RUN_STATUSES, VERDICTS, type Run } from "@domain/runs/run";
import type { RunEvent } from "@domain/runs/timeline";

export class ContractError extends Error {
  constructor(what: string, cause: z.ZodError) {
    const first = cause.issues[0];
    const where = first?.path.join(".") ?? "response";
    super(`the server returned an unusable ${what}: ${where} — ${first?.message ?? "invalid"}`);
    this.name = "ContractError";
  }
}

function parse<T>(schema: z.ZodType<T>, value: unknown, what: string): T {
  const result = schema.safeParse(value);
  if (!result.success) throw new ContractError(what, result.error);
  return result.data;
}

const projectSchema = z.object({
  project_id: z.string().min(1),
  name: z.string().min(1),
  default_run_policy_id: z.string().nullish(),
});

const runSchema = z.object({
  run_id: z.string().min(1),
  project_id: z.string().min(1),
  // An unrecognised status is a server this client does not understand. Guessing
  // would put the UI in a state whose transitions it cannot reason about.
  status: z.enum(RUN_STATUSES),
  verdict: z.enum(VERDICTS).nullish(),
  plan_id: z.string().nullish(),
  plan_version: z.string().nullish(),
});

const runEventSchema = z.object({
  event_id: z.string().min(1),
  run_id: z.string().min(1),
  sequence: z.number().int().nonnegative(),
  type: z.string().min(1),
  occurred_at: z.string().min(1),
  payload: z.record(z.string(), z.unknown()).default({}),
  request_id: z.string().nullish(),
});

/** `next_after` is the cursor to resume from; empty events means fully caught up. */
const runEventPageSchema = z.object({
  events: z.array(z.unknown()),
  next_after: z.number().int().nonnegative(),
});

export function toProject(value: unknown): Project {
  const raw = parse(projectSchema, value, "project");
  return {
    projectId: raw.project_id,
    name: raw.name,
    defaultRunPolicyId: raw.default_run_policy_id ?? null,
  };
}

export function toProjects(value: unknown): Project[] {
  return parse(z.array(z.unknown()), value, "project list").map(toProject);
}

export function toRun(value: unknown): Run {
  const raw = parse(runSchema, value, "run");
  return {
    runId: raw.run_id,
    projectId: raw.project_id,
    status: raw.status,
    verdict: raw.verdict ?? null,
    planId: raw.plan_id ?? null,
    planVersion: raw.plan_version ?? null,
  };
}

export function toRunEvent(value: unknown): RunEvent {
  const raw = parse(runEventSchema, value, "run event");
  return {
    eventId: raw.event_id,
    sequence: raw.sequence,
    runId: raw.run_id,
    type: raw.type,
    occurredAt: raw.occurred_at,
    payload: raw.payload,
  };
}

export function toRunEventPage(value: unknown): { events: RunEvent[]; nextAfter: number } {
  const page = parse(runEventPageSchema, value, "run event page");
  return { events: page.events.map(toRunEvent), nextAfter: page.next_after };
}


const memoryStatusSchema = z.object({
  project_id: z.string().min(1),
  environment_id: z.string().min(1),
  graph_available: z.boolean(),
  graph_schema_version: z.string().min(1),
  durable_candidates: z.number().int().nonnegative(),
  actionable_candidates: z.number().int().nonnegative(),
  sync_pending: z.number().int().nonnegative(),
  sync_failed: z.number().int().nonnegative(),
  by_status: z.record(z.string(), z.number().int().nonnegative()),
});

export function toMemoryStatus(value: unknown): MemoryStatus {
  const raw = parse(memoryStatusSchema, value, "memory status");
  return {
    projectId: raw.project_id,
    environmentId: raw.environment_id,
    graphAvailable: raw.graph_available,
    graphSchemaVersion: raw.graph_schema_version,
    durableCandidates: raw.durable_candidates,
    actionableCandidates: raw.actionable_candidates,
    syncPending: raw.sync_pending,
    syncFailed: raw.sync_failed,
    byStatus: raw.by_status,
  };
}


const findingSchema = z.object({
  criterion_id: z.string().min(1),
  step_id: z.string().nullish(),
  outcome: z.enum(["met", "not_met", "unverified"]),
  failure_kind: z.enum(["product", "plan", "environment", "policy"]).nullish(),
  deterministic_observation: z.string().nullish(),
  root_cause_hypothesis: z.string().nullish(),
  model_derived: z.boolean(),
  model_name: z.string().nullish(),
});

const reportSchema = z.object({
  run_id: z.string().min(1),
  criteria: z.array(z.unknown()).default([]),
});

const artifactSchema = z.object({
  artifact_id: z.string().min(1),
  kind: z.string().min(1),
  relative_path: z.string().min(1),
  sha256: z.string().min(1),
  size_bytes: z.number().int().nonnegative(),
  step_id: z.string().nullish(),
});

const failureContextSchema = z.object({
  run_id: z.string().min(1),
  evidence_set_id: z.string().nullish(),
  artifacts: z.array(z.unknown()).default([]),
});

function toFinding(value: unknown): Finding {
  const raw = parse(findingSchema, value, "finding");
  return {
    criterionId: raw.criterion_id,
    stepId: raw.step_id ?? null,
    outcome: raw.outcome,
    failureKind: raw.failure_kind ?? null,
    deterministicObservation: raw.deterministic_observation ?? null,
    rootCauseHypothesis: raw.root_cause_hypothesis ?? null,
    modelDerived: raw.model_derived,
    modelName: raw.model_name ?? null,
  };
}

function toArtifact(value: unknown): Artifact {
  const raw = parse(artifactSchema, value, "artifact");
  return {
    artifactId: raw.artifact_id,
    kind: raw.kind,
    relativePath: raw.relative_path,
    sha256: raw.sha256,
    sizeBytes: raw.size_bytes,
    stepId: raw.step_id ?? null,
  };
}

/** The report and the failure context are two endpoints and one screen. Merged here so
 * the ViewModel deals in one shape rather than in two transport documents. */
export function toRunReport(report: unknown, failureContext: unknown): RunReport {
  const parsedReport = parse(reportSchema, report, "run report");
  const parsedContext = parse(failureContextSchema, failureContext, "failure context");
  return {
    runId: parsedReport.run_id,
    findings: parsedReport.criteria.map(toFinding),
    artifacts: parsedContext.artifacts.map(toArtifact),
    evidenceSetId: parsedContext.evidence_set_id ?? null,
  };
}


const storySchema = z.object({
  story_id: z.string().min(1),
  project_id: z.string().min(1),
  actor: z.string().min(1),
  goal: z.string().min(1),
  acceptance_criteria: z.array(
    z.object({
      criterion_id: z.string().min(1),
      description: z.string().min(1),
      verification_hint: z.string().nullish(),
    }),
  ),
});

export function toStory(value: unknown): UserStory {
  const raw = parse(storySchema, value, "story");
  return {
    storyId: raw.story_id,
    projectId: raw.project_id,
    actor: raw.actor,
    goal: raw.goal,
    acceptanceCriteria: raw.acceptance_criteria.map((criterion) => ({
      criterionId: criterion.criterion_id,
      description: criterion.description,
      verificationHint: criterion.verification_hint ?? null,
    })),
  };
}

export function toStories(value: unknown): UserStory[] {
  return parse(z.array(z.unknown()), value, "story list").map(toStory);
}


/** Compiling returns the portable plan document; the UI only needs its identity. */
const compiledPlanSchema = z.object({
  plan_id: z.string().min(1),
  plan_version: z.string().min(1),
});

export function toCompiledPlan(value: unknown): { planId: string; planVersion: string } {
  const raw = parse(compiledPlanSchema, value, "compiled plan");
  return { planId: raw.plan_id, planVersion: raw.plan_version };
}
