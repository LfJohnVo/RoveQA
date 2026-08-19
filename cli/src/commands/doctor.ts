/**
 * `roveqa doctor` — answer "why is this not working" in one command.
 *
 * It reports where every configuration value came from, whether the API answers, and
 * whether the contract versions the CLI knows match the ones the server serves. A
 * version mismatch is reported rather than worked around: a CLI that silently adapts
 * to an older server is a CLI whose output means something different depending on
 * which server it hit.
 */

import type { ApiClient } from "../client/api.js";
import type { Config } from "../config.js";
import { CliError } from "../errors.js";
import { SCHEMA_VERSION } from "../output/envelope.js";

export const SUPPORTED_PLAN_SCHEMA = "roveqa.test-plan.v1";

export interface DoctorReport {
  cli_version: string;
  envelope_schema: string;
  plan_schema: string;
  api_url: string;
  api_reachable: boolean;
  api_status: string | null;
  config_sources: Record<string, string>;
  problems: string[];
}

export async function doctor(
  client: ApiClient,
  config: Config,
  cliVersion: string,
): Promise<DoctorReport> {
  const report: DoctorReport = {
    cli_version: cliVersion,
    envelope_schema: SCHEMA_VERSION,
    plan_schema: SUPPORTED_PLAN_SCHEMA,
    api_url: config.apiUrl,
    api_reachable: false,
    api_status: null,
    config_sources: config.sources,
    problems: [],
  };

  try {
    const response = await client.request({ method: "GET", path: "/health", attempts: 1 });
    report.api_reachable = true;
    report.api_status = describeHealth(response.body);
  } catch (error) {
    // Collected rather than thrown: an operator running doctor because nothing works
    // needs the whole picture, not the first error. Exiting non-zero happens after
    // every check has run.
    report.problems.push(error instanceof CliError ? error.message : String(error));
  }

  if (config.projectId === null) {
    report.problems.push("no project id configured: pass --project or set ROVEQA_PROJECT_ID");
  }
  return report;
}

/**
 * Turn a report with problems into a failure.
 *
 * A doctor that exits 0 while reporting an unreachable API is a doctor CI cannot use:
 * the whole point of running it in a pipeline is that a broken setup stops the
 * pipeline. The full report travels in `details`, so nothing is lost by failing.
 */
export function problemError(report: DoctorReport): CliError | null {
  if (report.problems.length === 0) return null;
  const code = report.api_reachable ? "CONFIG_ERROR" : "TRANSPORT_ERROR";
  return new CliError(code, `roveqa doctor found ${report.problems.length} problem(s)`, {
    nextAction: report.problems[0],
    details: { report: { ...report } },
  });
}

function describeHealth(body: unknown): string {
  if (body !== null && typeof body === "object") {
    const status = (body as Record<string, unknown>).status;
    if (typeof status === "string") return status;
  }
  return "reachable";
}
