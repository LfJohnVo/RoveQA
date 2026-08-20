/**
 * The only place in the browser that knows an endpoint exists.
 *
 * Everything above it receives domain types, so a route or a field name changing is a
 * one-file edit rather than a hunt through components. That is also what makes the
 * Phase 10 gate testable: a view cannot import an API client it has no reason to know
 * about.
 *
 * Mutations carry an `Idempotency-Key`. A user who double-clicks "Start run", or a
 * browser that retries a request whose response was lost, must not get two runs — the
 * server deduplicates on that key (docs/12), and the client is the only side that can
 * keep it stable across the retry.
 */

import type {
  MemoryGateway,
  ProjectGateway,
  RunGateway,
  StartRunInput,
  StoryGateway,
  DraftStory,
  CompiledPlan,
} from "@application/ports/gateways";
import type { MemoryStatus } from "@domain/knowledge/memory";
import type { Project } from "@domain/projects/project";
import type { UserStory } from "@domain/qa/story";
import type { RunReport } from "@domain/runs/findings";
import type { Run } from "@domain/runs/run";
import type { RunEvent } from "@domain/runs/timeline";

import {
  toCompiledPlan,
  toMemoryStatus,
  toProject,
  toProjects,
  toRun,
  toRunEventPage,
  toRunReport,
  toStories,
  toStory,
} from "./schemas";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  /** Whether showing this to a user is worth more than showing "something failed". */
  get isExpected(): boolean {
    return this.status >= 400 && this.status < 500;
  }
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

const DEFAULT_BASE_URL = "";

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  async request(
    method: string,
    path: string,
    options: { body?: unknown; idempotencyKey?: string } = {},
  ): Promise<unknown> {
    const headers: Record<string, string> = { accept: "application/json" };
    if (options.body !== undefined) headers["content-type"] = "application/json";
    if (options.idempotencyKey !== undefined) {
      headers["Idempotency-Key"] = options.idempotencyKey;
    }

    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: options.body === undefined ? null : JSON.stringify(options.body),
    });

    if (!response.ok) throw await toApiError(response);
    if (response.status === 204) return null;
    return (await response.json()) as unknown;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  // The server's problem envelope carries a machine-readable code and a message that
  // is already safe to show. Falling back to the status text keeps a proxy's plain
  // 502 from surfacing as an empty error nobody can act on.
  let code = `http_${response.status}`;
  let message = response.statusText || "the request failed";
  try {
    const body: unknown = await response.json();
    if (body !== null && typeof body === "object") {
      const record = body as Record<string, unknown>;
      const error = record.error;
      if (error !== null && typeof error === "object") {
        const detail = error as Record<string, unknown>;
        if (typeof detail.code === "string") code = detail.code;
        if (typeof detail.message === "string") message = detail.message;
      }
    }
  } catch {
    // A body that is not JSON tells us nothing extra; the status still does.
  }
  return new ApiError(response.status, code, message);
}

export class HttpProjectGateway implements ProjectGateway {
  private readonly client: ApiClient;

  constructor(client: ApiClient) {
    this.client = client;
  }

  async list(limit: number): Promise<Project[]> {
    return toProjects(await this.client.request("GET", `/api/v1/projects?limit=${limit}`));
  }

  async get(projectId: string): Promise<Project> {
    return toProject(
      await this.client.request("GET", `/api/v1/projects/${encodeURIComponent(projectId)}`),
    );
  }
}

export class HttpRunGateway implements RunGateway {
  private readonly client: ApiClient;

  constructor(client: ApiClient) {
    this.client = client;
  }

  async get(runId: string): Promise<Run> {
    return toRun(await this.client.request("GET", `/api/v1/runs/${encodeURIComponent(runId)}`));
  }

  async events(runId: string, after: number): Promise<RunEvent[]> {
    const page = toRunEventPage(
      await this.client.request(
        "GET",
        `/api/v1/runs/${encodeURIComponent(runId)}/events?after=${after}`,
      ),
    );
    return page.events;
  }

  async report(runId: string): Promise<RunReport> {
    const id = encodeURIComponent(runId);
    // Requested together: the screen shows conclusions beside the evidence for them,
    // and fetching them in sequence would render the findings against an empty
    // evidence list for a frame.
    const [report, failureContext] = await Promise.all([
      this.client.request("GET", `/api/v1/runs/${id}/report`),
      this.client.request("GET", `/api/v1/runs/${id}/failure-context`),
    ]);
    return toRunReport(report, failureContext);
  }

  async start(input: StartRunInput): Promise<Run> {
    const body: Record<string, string> = { project_id: input.projectId };
    if (input.planId !== undefined) body.plan_id = input.planId;
    if (input.planVersion !== undefined) body.plan_version = input.planVersion;
    if (input.environmentId !== undefined) body.environment_id = input.environmentId;

    return toRun(
      await this.client.request("POST", "/api/v1/runs", {
        body,
        idempotencyKey: input.idempotencyKey,
      }),
    );
  }

  async pause(runId: string): Promise<void> {
    await this.command(runId, "pause");
  }

  async resume(runId: string): Promise<void> {
    await this.command(runId, "resume");
  }

  async cancel(runId: string): Promise<void> {
    await this.command(runId, "cancel");
  }

  private async command(runId: string, action: string): Promise<void> {
    await this.client.request("POST", `/api/v1/runs/${encodeURIComponent(runId)}/${action}`);
  }
}


export class HttpMemoryGateway implements MemoryGateway {
  private readonly client: ApiClient;

  constructor(client: ApiClient) {
    this.client = client;
  }

  async status(projectId: string, environmentId: string): Promise<MemoryStatus> {
    return toMemoryStatus(
      await this.client.request(
        "GET",
        `/api/v1/projects/${encodeURIComponent(projectId)}/memory/status` +
          `?environment_id=${encodeURIComponent(environmentId)}`,
      ),
    );
  }
}


export class HttpStoryGateway implements StoryGateway {
  private readonly client: ApiClient;

  constructor(client: ApiClient) {
    this.client = client;
  }

  async list(projectId: string): Promise<UserStory[]> {
    return toStories(
      await this.client.request(
        "GET",
        `/api/v1/projects/${encodeURIComponent(projectId)}/stories`,
      ),
    );
  }

  async get(storyId: string): Promise<UserStory> {
    return toStory(
      await this.client.request("GET", `/api/v1/stories/${encodeURIComponent(storyId)}`),
    );
  }

  async create(draft: DraftStory): Promise<UserStory> {
    return toStory(
      await this.client.request(
        "POST",
        `/api/v1/projects/${encodeURIComponent(draft.projectId)}/stories`,
        {
          body: {
            actor: draft.actor,
            goal: draft.goal,
            acceptance_criteria: draft.acceptanceCriteria.map((criterion) => ({
              criterion_id: criterion.criterionId,
              description: criterion.description,
              // Omitted rather than sent as null when absent: the server treats a
              // missing hint as "judge this with a model", and an explicit null would
              // be saying the same thing in a shape the schema does not promise.
              ...(criterion.verificationHint === null
                ? {}
                : { verification_hint: criterion.verificationHint }),
            })),
          },
        },
      ),
    );
  }

  async compile(storyId: string, runPolicyId: string): Promise<CompiledPlan> {
    const document = await this.client.request(
      "POST",
      `/api/v1/stories/${encodeURIComponent(storyId)}/plans`,
      { body: { run_policy_id: runPolicyId } },
    );
    return toCompiledPlan(document);
  }
}
