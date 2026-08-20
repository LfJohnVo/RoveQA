/**
 * `roveqa memory status|validate|rebuild|sync` — operate the learned-memory graph.
 *
 * A thin client, like every other command: the CLI holds no memory logic and never
 * speaks to FalkorDB. It calls the public API and validates what comes back.
 *
 * Responses are parsed rather than cast. These commands are the ones an operator runs
 * when something is already wrong, so a malformed answer has to surface as a
 * transport error — not as `undefined` rendered into a report that reads healthy.
 */

import type { ApiClient } from "../client/api.js";
import { CliError } from "../errors.js";

export interface MemoryStatus {
  project_id: string;
  environment_id: string;
  graph_available: boolean;
  graph_schema_version: string;
  durable_candidates: number;
  actionable_candidates: number;
  sync_pending: number;
  sync_failed: number;
  by_status: Record<string, number>;
}

export interface MemoryValidation {
  project_id: string;
  environment_id: string;
  healthy: boolean;
  problems: string[];
  status: MemoryStatus;
}

export interface MemoryRebuild {
  project_id: string;
  environment_id: string;
  materialized: number;
  forgotten: number;
  failed: number;
  graph_available: boolean;
}

function scopePath(projectId: string, environmentId: string, action: string): string {
  return (
    `/api/v1/projects/${encodeURIComponent(projectId)}/memory/${action}` +
    `?environment_id=${encodeURIComponent(environmentId)}`
  );
}

function record(value: unknown, what: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new CliError("TRANSPORT_ERROR", `the server returned a ${what} that is not an object`);
  }
  return value as Record<string, unknown>;
}

function num(source: Record<string, unknown>, key: string): number {
  const value = source[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new CliError("TRANSPORT_ERROR", `the server returned a non-numeric ${key}`);
  }
  return value;
}

function bool(source: Record<string, unknown>, key: string): boolean {
  const value = source[key];
  if (typeof value !== "boolean") {
    throw new CliError("TRANSPORT_ERROR", `the server returned a non-boolean ${key}`);
  }
  return value;
}

function text(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new CliError("TRANSPORT_ERROR", `the server returned an empty ${key}`);
  }
  return value;
}

export function parseStatus(value: unknown): MemoryStatus {
  const body = record(value, "memory status");
  const counts = record(body.by_status ?? {}, "status breakdown");
  const byStatus: Record<string, number> = {};
  for (const [status, total] of Object.entries(counts)) {
    if (typeof total !== "number") {
      throw new CliError("TRANSPORT_ERROR", `the server returned a non-numeric count for ${status}`);
    }
    byStatus[status] = total;
  }
  return {
    project_id: text(body, "project_id"),
    environment_id: text(body, "environment_id"),
    graph_available: bool(body, "graph_available"),
    graph_schema_version: text(body, "graph_schema_version"),
    durable_candidates: num(body, "durable_candidates"),
    actionable_candidates: num(body, "actionable_candidates"),
    sync_pending: num(body, "sync_pending"),
    sync_failed: num(body, "sync_failed"),
    by_status: byStatus,
  };
}

export function parseValidation(value: unknown): MemoryValidation {
  const body = record(value, "memory validation");
  const problems = body.problems;
  if (!Array.isArray(problems) || problems.some((item) => typeof item !== "string")) {
    throw new CliError("TRANSPORT_ERROR", "the server returned problems that are not strings");
  }
  return {
    project_id: text(body, "project_id"),
    environment_id: text(body, "environment_id"),
    healthy: bool(body, "healthy"),
    problems: problems as string[],
    status: parseStatus(body.status),
  };
}

export function parseRebuild(value: unknown): MemoryRebuild {
  const body = record(value, "memory rebuild report");
  return {
    project_id: text(body, "project_id"),
    environment_id: text(body, "environment_id"),
    materialized: num(body, "materialized"),
    forgotten: num(body, "forgotten"),
    failed: num(body, "failed"),
    graph_available: bool(body, "graph_available"),
  };
}

export async function memoryStatus(
  client: ApiClient,
  projectId: string,
  environmentId: string,
): Promise<MemoryStatus> {
  const response = await client.request({
    method: "GET",
    path: scopePath(projectId, environmentId, "status"),
  });
  return parseStatus(response.body);
}

export async function memoryValidate(
  client: ApiClient,
  projectId: string,
  environmentId: string,
): Promise<MemoryValidation> {
  const response = await client.request({
    method: "POST",
    path: scopePath(projectId, environmentId, "validate"),
  });
  return parseValidation(response.body);
}

export async function memoryRebuild(
  client: ApiClient,
  projectId: string,
  environmentId: string,
): Promise<MemoryRebuild> {
  const response = await client.request({
    method: "POST",
    path: scopePath(projectId, environmentId, "rebuild"),
  });
  return parseRebuild(response.body);
}

export async function memorySync(
  client: ApiClient,
  projectId: string,
  environmentId: string,
): Promise<MemoryRebuild> {
  const response = await client.request({
    method: "POST",
    path: scopePath(projectId, environmentId, "sync"),
  });
  return parseRebuild(response.body);
}

export function renderStatus(status: MemoryStatus): string {
  const lines = [
    `project        ${status.project_id} (${status.environment_id})`,
    `graph          ${status.graph_available ? "available" : "UNAVAILABLE"} (${status.graph_schema_version})`,
    `knowledge      ${String(status.durable_candidates)} durable, ${String(status.actionable_candidates)} actionable`,
    `projection     ${String(status.sync_pending)} pending, ${String(status.sync_failed)} failed`,
  ];
  for (const [name, total] of Object.entries(status.by_status)) {
    if (total > 0) lines.push(`  ${name.padEnd(13)}${String(total)}`);
  }
  return `${lines.join("\n")}\n`;
}

export function renderValidation(validation: MemoryValidation): string {
  const head = validation.healthy
    ? "memory is consistent with its projection\n"
    : `${String(validation.problems.length)} problem(s):\n${validation.problems.map((problem) => `  - ${problem}\n`).join("")}`;
  return head + renderStatus(validation.status);
}

export function renderRebuild(report: MemoryRebuild): string {
  const warning = report.graph_available
    ? ""
    : "  graph unavailable: the backlog kept the work, run again when it is back\n";
  return (
    `${String(report.materialized)} projected, ${String(report.forgotten)} removed, ` +
    `${String(report.failed)} failed\n${warning}`
  );
}
