/**
 * What the application layer is allowed to ask for.
 *
 * ViewModels depend on these, never on `fetch`, a URL, or an event name. That is what
 * makes the Phase 10 gate — "Views do not import API clients" — enforceable rather
 * than aspirational: there is nothing for a view to import, because the only thing
 * that knows an endpoint exists lives behind these types.
 *
 * Every method returns domain types. Transport shapes are validated and mapped in
 * `infrastructure/api`, so a server that changes a field breaks in one place with a
 * message naming the field.
 */

import type { Project } from "@domain/projects/project";
import type { ConnectionState } from "@domain/runs/connection";
import type { Run } from "@domain/runs/run";
import type { MemoryStatus } from "@domain/knowledge/memory";
import type { AcceptanceCriterion, UserStory } from "@domain/qa/story";
import type { RunReport } from "@domain/runs/findings";
import type { RunEvent } from "@domain/runs/timeline";

export interface NewProjectInput {
  name: string;
  /**
   * Where runs of this project may go. Required, and there is no empty default: the
   * allowlist is the only thing that knows which application is under test, so a
   * project created without one can list, show and do nothing.
   */
  allowedOrigins: readonly string[];
  maxDurationSeconds: number;
  maxActions: number;
  maxModelCalls: number;
  /** Whether the agent may click, type and submit. Off by default, on the server too:
   * a policy that permits writes is a decision somebody makes, not one they inherit. */
  destructiveActions: boolean;
}

export interface ProjectGateway {
  list(limit: number): Promise<Project[]>;
  get(projectId: string): Promise<Project>;

  /**
   * Create the project and its first run policy, in that order.
   *
   * One method rather than two because half of it is not usable: a project with no
   * policy cannot compile a plan or start a run, and leaving the second call to the
   * caller is how the UI ends up full of projects that look real and refuse to work.
   */
  create(input: NewProjectInput): Promise<Project>;
}

export interface StartRunInput {
  projectId: string;
  /**
   * Generated once per user intent and reused across every retry of it.
   *
   * Required rather than optional, and supplied by the caller rather than by the
   * gateway: a key minted inside the call would be a new key on each attempt, so a
   * lost response would create a second run — the exact failure the key exists to
   * prevent (docs/12).
   */
  idempotencyKey: string;
  planId?: string;
  planVersion?: string;
  environmentId?: string;
}

export interface RunGateway {
  get(runId: string): Promise<Run>;

  /**
   * Durable events from `after` onward.
   *
   * The baseline a reload rebuilds from, and what a reconnect catches up with. It is
   * REST rather than replayed over the socket because the durable log is the
   * authority; the socket only makes it timely.
   */
  events(runId: string, after: number): Promise<RunEvent[]>;

  /** What the run concluded, and the evidence behind it. Read separately from the
   * run itself: a finished run's findings do not change, so they are cacheable in a
   * way the live status is not. */
  report(runId: string): Promise<RunReport>;

  start(input: StartRunInput): Promise<Run>;
  pause(runId: string): Promise<void>;
  resume(runId: string): Promise<void>;
  cancel(runId: string): Promise<void>;
}

export interface RunSubscription {
  close(): void;
}

export interface RunEventStream {
  /**
   * Subscribe to a run's live events.
   *
   * `onEvents` may deliver an event the caller already has: the durable timeline
   * dedupes by sequence, so overlap is safe and a gap is not. An adapter that tried to
   * avoid overlap would risk dropping an event that arrived during the handover.
   */
  subscribe(
    runId: string,
    handlers: {
      onEvents: (events: readonly RunEvent[]) => void;
      onConnectionChange: (state: ConnectionState) => void;
    },
  ): RunSubscription;
}


export interface MemoryGateway {
  /**
   * What this project has learned, and whether the projection reflects it.
   *
   * Answered from PostgreSQL, so it still answers while the graph is down — which is
   * exactly when someone opens this screen. The frontend never talks to FalkorDB
   * (`plans/phase-10-frontend-mvvm.md`); it reads the same admin API the CLI does.
   */
  status(projectId: string, environmentId: string): Promise<MemoryStatus>;
}


export interface DraftStory {
  projectId: string;
  actor: string;
  goal: string;
  acceptanceCriteria: readonly AcceptanceCriterion[];
}

export interface CompiledPlan {
  planId: string;
  planVersion: string;
}

export interface StoryGateway {
  list(projectId: string): Promise<UserStory[]>;
  get(storyId: string): Promise<UserStory>;
  create(draft: DraftStory): Promise<UserStory>;

  /** Compile a story into an immutable plan version.
   *
   * Deterministic and model-free, which is what makes "a known story passes or fails
   * reproducibly" true — so it returns the version it created rather than a job id.
   *
   * The policy is required by the server: a plan with no policy and no budget is one
   * whose limits nobody chose, and it refuses to create one. */
  compile(storyId: string, runPolicyId: string): Promise<CompiledPlan>;
}
