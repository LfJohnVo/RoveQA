#!/usr/bin/env node
/**
 * The CLI entrypoint.
 *
 * Every command returns a value or throws a `CliError`; this file is the only place
 * that writes the envelope, maps an error to an exit code, and touches stdout. That
 * is what makes "exactly one JSON value on stdout" a property of the program rather
 * than a habit each command has to remember.
 *
 * Argument parsing uses `node:util`'s `parseArgs`. A CLI framework would bring its
 * own output conventions — help text on stdout, coloured errors — and the whole
 * contract here is that nothing writes to stdout except the envelope.
 */

import { randomUUID } from "node:crypto";
import { parseArgs } from "node:util";

import { ApiClient } from "./client/api.js";
import { loadConfig, type Config, type ConfigFlags } from "./config.js";
import { CliError, unclassified, usage } from "./errors.js";
import { doctor, problemError } from "./commands/doctor.js";
import { hasErrors, lintPlan, readPlanFile, scaffoldPlan } from "./commands/plan.js";
import {
  cancelRun,
  createRun,
  failureContext,
  getRun,
  rerun,
  waitForRun,
  type RunState,
} from "./commands/run.js";
import { materialize, type BundleManifest } from "./bundle/materialize.js";
import {
  diagnostic,
  emit,
  errorEnvelope,
  processWriter,
  successEnvelope,
  type Envelope,
  type OutputMode,
  type Writer,
} from "./output/envelope.js";
import { EXIT_OK, exitCodeFor, exitCodeForVerdict, isTerminalVerdict } from "./output/exit-codes.js";

export const CLI_VERSION = "0.1.0";

export interface CommandResult {
  data: unknown;
  text: string;
  /** Overrides the default 0; used by verdict-bearing commands. */
  exitCode?: number;
}

type Values = Record<string, string | boolean | undefined>;

const OPTIONS = {
  output: { type: "string" as const },
  "api-url": { type: "string" as const },
  project: { type: "string" as const },
  environment: { type: "string" as const },
  "request-timeout-ms": { type: "string" as const },
  "policy-id": { type: "string" as const },
  "plan-id": { type: "string" as const },
  plan: { type: "string" as const },
  "idempotency-key": { type: "string" as const },
  timeout: { type: "string" as const },
  out: { type: "string" as const },
  name: { type: "string" as const },
  help: { type: "boolean" as const },
};

export async function run(argv: string[], writer: Writer = processWriter): Promise<number> {
  let mode: OutputMode = "text";
  const requestId = randomUUID();

  try {
    const parsed = parseArgs({ args: argv, options: OPTIONS, allowPositionals: true });
    mode = outputMode(parsed.values.output);

    const result = await dispatch(parsed.positionals, parsed.values, requestId, writer);
    emit(writer, mode, successEnvelope(requestId, result.data), () => result.text);
    return result.exitCode ?? EXIT_OK;
  } catch (error) {
    const failure = toCliError(error);
    emit(
      writer,
      mode,
      errorEnvelope(requestId, {
        code: failure.code,
        message: failure.message,
        next_action: failure.nextAction,
        details: failure.details,
      }),
      (envelope) => renderError(envelope),
    );
    return exitCodeFor(failure.code);
  }
}

async function dispatch(
  positionals: string[],
  values: Values,
  requestId: string,
  writer: Writer,
): Promise<CommandResult> {
  const [group, action, ...rest] = positionals;

  if (values.help === true || group === undefined) {
    throw usage("no command given", "Try: roveqa doctor --output json");
  }

  switch (`${group} ${action ?? ""}`.trim()) {
    case "plan scaffold":
      return planScaffold(values);
    case "plan lint":
      return planLint(rest, writer);
    case "doctor":
      return await doctorCommand(values, requestId);
    case "run create":
      return await runCreate(values, requestId, writer);
    case "run get":
      return await runGet(rest, values, requestId);
    case "run wait":
      return await runWait(rest, values, requestId, writer);
    case "run cancel":
      return await runCancel(rest, values, requestId);
    case "run failure":
      return await runFailure(rest, values, requestId, writer);
    case "run rerun":
      return await runRerun(rest, values, requestId);
    default:
      throw usage(
        `unknown command: ${[group, action].filter(Boolean).join(" ")}`,
        "Known commands: doctor, plan scaffold, plan lint, run create, run get, " +
          "run wait, run cancel, run failure, run rerun",
      );
  }
}

// --- local commands -------------------------------------------------------------

function planScaffold(values: Values): CommandResult {
  const config = loadConfig(configFlags(values));
  const projectId = asString(values.project) ?? config.projectId;
  if (projectId === null || projectId === undefined) {
    throw usage("a project id is required", "Pass --project <id> or set ROVEQA_PROJECT_ID.");
  }

  const plan = scaffoldPlan({
    name: asString(values.name) ?? "New plan",
    projectId,
    runPolicyId: asString(values["policy-id"]),
  });
  // Text mode prints the plan itself: `roveqa plan scaffold > plan.json` has to
  // produce a usable file in both modes.
  return { data: plan, text: `${JSON.stringify(plan, null, 2)}\n` };
}

function planLint(rest: string[], writer: Writer): CommandResult {
  const path = rest[0];
  if (path === undefined) {
    throw usage("a plan file is required", "Try: roveqa plan lint plan.json");
  }

  const findings = lintPlan(readPlanFile(path));
  if (hasErrors(findings)) {
    throw new CliError("VALIDATION_ERROR", `${path} is not a valid test plan`, {
      nextAction: "Fix the reported errors and run plan lint again.",
      details: { findings },
    });
  }

  for (const finding of findings) {
    diagnostic(writer, `warning ${finding.path}: ${finding.message}`);
  }
  return {
    data: { path, valid: true, findings },
    text: `${path}: valid (${findings.length} warning(s))\n`,
  };
}

// --- API commands ---------------------------------------------------------------

async function doctorCommand(values: Values, requestId: string): Promise<CommandResult> {
  const { client, config } = connect(values, requestId);
  const report = await doctor(client, config, CLI_VERSION);
  const failure = problemError(report);
  if (failure !== null) throw failure;

  const text = [
    `cli        ${report.cli_version}`,
    `api        ${report.api_url} (${report.api_reachable ? report.api_status : "unreachable"})`,
    `contracts  ${report.envelope_schema}, ${report.plan_schema}`,
    ...report.problems.map((problem) => `problem    ${problem}`),
    "",
  ].join("\n");
  // Problems are reported, not thrown: doctor exists to describe a broken setup.
  return { data: report, text };
}

async function runCreate(values: Values, requestId: string, writer: Writer): Promise<CommandResult> {
  const { client, config } = connect(values, requestId);
  const planPath = asString(values.plan);
  if (planPath === undefined) {
    throw usage("a plan file is required", "Try: roveqa run create --plan plan.json");
  }

  const plan = readPlanFile(planPath);
  const findings = lintPlan(plan);
  if (hasErrors(findings)) {
    // Refusing here saves a round trip and, more importantly, a run: an invalid plan
    // would either be rejected by the server or executed as something nobody meant.
    throw new CliError("VALIDATION_ERROR", `${planPath} is not a valid test plan`, {
      nextAction: "Run roveqa plan lint on it and fix the errors.",
      details: { findings },
    });
  }

  const projectId = asString(values.project) ?? config.projectId ?? planProjectId(plan);
  if (projectId === null) {
    throw usage("a project id is required", "Pass --project <id> or set it in the plan.");
  }

  diagnostic(writer, `importing plan from ${planPath}`);
  const imported = await client.request({
    method: "POST",
    path: "/api/v1/plans",
    body: {
      plan,
      ...(asString(values["plan-id"]) ? { plan_id: asString(values["plan-id"]) } : {}),
    },
  });
  const { planId, planVersion } = parsePlanIdentity(imported.body);

  const created = await createRun(client, {
    projectId,
    planId,
    planVersion,
    environmentId: config.environmentId ?? undefined,
    idempotencyKey: asString(values["idempotency-key"]),
  });

  return {
    data: { ...created, plan_id: planId, plan_version: planVersion },
    text: `run ${created.run_id} created for plan ${planId}@${planVersion}\n`,
  };
}

async function runGet(rest: string[], values: Values, requestId: string): Promise<CommandResult> {
  const runId = requireRunId(rest);
  const { client } = connect(values, requestId);
  const state = await getRun(client, runId);
  return { data: state, text: renderRun(state), exitCode: verdictExit(state) };
}

async function runWait(
  rest: string[],
  values: Values,
  requestId: string,
  writer: Writer,
): Promise<CommandResult> {
  const runId = requireRunId(rest);
  const { client } = connect(values, requestId);
  const timeout = asString(values.timeout);

  // Ctrl-C detaches. The signal stops the polling loop; it never signals the server,
  // because a run must not end because someone closed a terminal.
  const controller = new AbortController();
  const onInterrupt = (): void => {
    diagnostic(writer, "interrupted: detaching from the run, which keeps going");
    controller.abort();
  };
  process.once("SIGINT", onInterrupt);
  process.once("SIGTERM", onInterrupt);

  try {
    const outcome = await waitForRun(client, runId, {
      ...(timeout === undefined ? {} : { timeoutMs: Number(timeout) }),
      signal: controller.signal,
    });

    if (outcome.timedOut) {
      throw new CliError("WAIT_TIMEOUT", `run ${runId} is still ${outcome.run.status}`, {
        nextAction: `roveqa run wait ${runId} --timeout <ms>`,
        details: { run_id: runId, status: outcome.run.status, verdict: null },
      });
    }
    return {
      data: outcome.run,
      text: renderRun(outcome.run),
      exitCode: verdictExit(outcome.run),
    };
  } finally {
    process.off("SIGINT", onInterrupt);
    process.off("SIGTERM", onInterrupt);
  }
}

async function runCancel(rest: string[], values: Values, requestId: string): Promise<CommandResult> {
  const runId = requireRunId(rest);
  const { client } = connect(values, requestId);
  await cancelRun(client, runId);
  return {
    // Cancellation is accepted, not applied: the workflow stops at its next safe
    // point, so reporting "cancelled" here would be a lie for a second or two.
    data: { run_id: runId, cancel_requested: true },
    text: `cancellation requested for ${runId}\n`,
  };
}

async function runFailure(
  rest: string[],
  values: Values,
  requestId: string,
  writer: Writer,
): Promise<CommandResult> {
  const runId = requireRunId(rest);
  const outDir = asString(values.out);
  if (outDir === undefined) {
    throw usage(
      "an output directory is required",
      `Try: roveqa run failure ${runId} --out ./bundle`,
    );
  }

  const { client } = connect(values, requestId);
  const manifest = await failureContext(client, runId);
  diagnostic(writer, `materializing the failure bundle for ${runId}`);

  const result = await materialize(manifest as BundleManifest, outDir, (artifact) =>
    // Raw bytes: an artifact is a screenshot or a trace, and JSON-decoding one would
    // corrupt exactly the evidence the bundle exists to preserve.
    client.requestBytes(`/api/v1/artifacts/${encodeURIComponent(artifact.artifact_id)}`),
  );

  return {
    data: { run_id: runId, ...result },
    text: `bundle written to ${result.directory} (${result.artifactCount} artifact(s))
`,
  };
}

async function runRerun(rest: string[], values: Values, requestId: string): Promise<CommandResult> {
  const runId = requireRunId(rest);
  const { client } = connect(values, requestId);
  const created = await rerun(client, runId, asString(values["idempotency-key"]));
  return {
    data: { ...created, source_run_id: runId },
    text: `run ${created.run_id} reruns ${runId}
`,
  };
}

// --- plumbing -------------------------------------------------------------------

function connect(values: Values, requestId: string): { client: ApiClient; config: Config } {
  const config = loadConfig(configFlags(values));
  return {
    config,
    client: new ApiClient({
      baseUrl: config.apiUrl,
      token: config.token,
      requestId,
      timeoutMs: config.requestTimeoutMs,
    }),
  };
}

function requireRunId(rest: string[]): string {
  const runId = rest[0];
  if (runId === undefined) throw usage("a run id is required");
  return runId;
}

function verdictExit(state: RunState): number {
  return isTerminalVerdict(state.verdict) ? exitCodeForVerdict(state.verdict) : EXIT_OK;
}

function renderRun(state: RunState): string {
  return `${state.run_id} ${state.status}${state.verdict ? ` ${state.verdict}` : ""}\n`;
}

function planProjectId(plan: unknown): string | null {
  if (plan === null || typeof plan !== "object") return null;
  const value = (plan as Record<string, unknown>).project_id;
  return typeof value === "string" ? value : null;
}

function parsePlanIdentity(body: unknown): { planId: string; planVersion: string } {
  if (body === null || typeof body !== "object") {
    throw new CliError("TRANSPORT_ERROR", "the server returned a plan that is not an object");
  }
  const record = body as Record<string, unknown>;
  const planId = record.plan_id;
  const planVersion = record.plan_version;
  if (typeof planId !== "string" || typeof planVersion !== "string") {
    throw new CliError("TRANSPORT_ERROR", "the server returned a plan without an identity");
  }
  return { planId, planVersion };
}

function configFlags(values: Values): ConfigFlags {
  const timeout = asString(values["request-timeout-ms"]);
  return {
    apiUrl: asString(values["api-url"]),
    projectId: asString(values.project),
    environmentId: asString(values.environment),
    requestTimeoutMs: timeout === undefined ? undefined : Number(timeout),
  };
}

function asString(value: string | boolean | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function outputMode(value: string | boolean | undefined): OutputMode {
  if (value === undefined) return "text";
  if (value === "json" || value === "text") return value;
  // Not a usage error thrown later: an unknown mode must not silently fall back to
  // text while the caller parses stdout as JSON.
  throw usage(`unknown --output value: ${String(value)}`, "Use --output json or --output text.");
}

function toCliError(error: unknown): CliError {
  if (error instanceof CliError) return error;
  if (error instanceof Error && error.message.includes("Unknown option")) {
    return usage(error.message);
  }
  return unclassified(error);
}

function renderError(envelope: Envelope): string {
  if (!("error" in envelope)) return "";
  const { code, message, next_action, details } = envelope.error;
  const lines = [`error: ${code}: ${message}`];
  const findings = (details as { findings?: Array<{ path: string; message: string }> } | null)
    ?.findings;
  for (const finding of findings ?? []) {
    lines.push(`  ${finding.path}: ${finding.message}`);
  }
  if (next_action) lines.push(`next: ${next_action}`);
  return `${lines.join("\n")}\n`;
}

// Errors go to stdout in text mode too, and that is deliberate: the envelope is the
// command's single result, and splitting it across two streams by outcome would make
// `roveqa ... --output json > result.json` lose exactly the failures.
const isEntrypoint = process.argv[1] !== undefined && import.meta.url.endsWith("main.js");
if (isEntrypoint) {
  run(process.argv.slice(2))
    .then((code) => {
      process.exitCode = code;
    })
    .catch((error: unknown) => {
      process.stderr.write(`fatal: ${String(error)}\n`);
      process.exitCode = exitCodeFor("INTERNAL_ERROR");
    });
}
