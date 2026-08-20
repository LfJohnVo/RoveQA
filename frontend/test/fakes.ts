/**
 * Doubles for the gateways.
 *
 * Deliberately behavioural rather than stubbed returns: the reconnect test needs a
 * socket it can drop and reopen, and the reload test needs a REST baseline that
 * genuinely holds the events the socket already delivered. A `vi.fn()` returning a
 * fixed array could not express either.
 */

import type {
  CompiledPlan,
  DraftStory,
  MemoryGateway,
  ProjectGateway,
  RunEventStream,
  RunGateway,
  RunSubscription,
  StartRunInput,
  StoryGateway,
} from "@application/ports/gateways";
import type { MemoryStatus } from "@domain/knowledge/memory";
import type { UserStory } from "@domain/qa/story";
import type { RunReport } from "@domain/runs/findings";
import type { ConnectionState } from "@domain/runs/connection";
import type { NewProjectInput } from "@application/ports/gateways";
import type { Project } from "@domain/projects/project";
import type { Run, RunStatus } from "@domain/runs/run";
import type { RunEvent } from "@domain/runs/timeline";

export function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    runId: "run-1",
    projectId: "proj-1",
    status: "running",
    verdict: null,
    planId: null,
    planVersion: null,
    ...overrides,
  };
}

export function makeEvent(sequence: number, type = "run.step"): RunEvent {
  return {
    eventId: `evt-${sequence}`,
    sequence,
    runId: "run-1",
    type,
    occurredAt: new Date(Date.UTC(2026, 7, 19, 12, 0, sequence)).toISOString(),
    payload: {},
  };
}

export class FakeProjectGateway implements ProjectGateway {
  private readonly projects: Project[];
  readonly created: NewProjectInput[] = [];
  /** Set to make `create` fail, the way a rejected origin does. */
  refuse: Error | null = null;

  constructor(projects: Project[] = []) {
    this.projects = projects;
  }

  list(): Promise<Project[]> {
    return Promise.resolve(this.projects);
  }

  get(projectId: string): Promise<Project> {
    const found = this.projects.find((project) => project.projectId === projectId);
    if (found === undefined) return Promise.reject(new NotFound());
    return Promise.resolve(found);
  }

  create(input: NewProjectInput): Promise<Project> {
    if (this.refuse !== null) return Promise.reject(this.refuse);
    this.created.push(input);
    // With a policy id, because the real gateway does not return one without it: the
    // whole point of the call is that the project comes back able to run.
    const project: Project = {
      projectId: `proj-${this.projects.length + 1}`,
      name: input.name,
      defaultRunPolicyId: "pol-1",
    };
    this.projects.push(project);
    return Promise.resolve(project);
  }
}

export class NotFound extends Error {
  readonly status = 404;
  constructor() {
    super("no such project");
  }
}

/** A durable log the socket and REST both read from, which is the real relationship. */
export class FakeRunGateway implements RunGateway {
  readonly commands: string[] = [];
  started: StartRunInput[] = [];
  run: Run;
  durable: RunEvent[];

  constructor(run: Run = makeRun(), durable: RunEvent[] = []) {
    this.run = run;
    this.durable = durable;
  }

  reads = 0;

  get(): Promise<Run> {
    this.reads += 1;
    return Promise.resolve(this.run);
  }

  events(_runId: string, after: number): Promise<RunEvent[]> {
    return Promise.resolve(this.durable.filter((event) => event.sequence > after));
  }

  report(runId: string): Promise<RunReport> {
    return Promise.resolve(
      this.reportValue ?? { runId, findings: [], artifacts: [], evidenceSetId: null },
    );
  }

  reportValue: RunReport | null = null;

  start(input: StartRunInput): Promise<Run> {
    this.started.push(input);
    return Promise.resolve(this.run);
  }

  pause(): Promise<void> {
    this.commands.push("pause");
    return Promise.resolve();
  }

  resume(): Promise<void> {
    this.commands.push("resume");
    return Promise.resolve();
  }

  cancel(): Promise<void> {
    this.commands.push("cancel");
    return Promise.resolve();
  }

  setStatus(status: RunStatus): void {
    this.run = { ...this.run, status };
  }
}

/** A stream a test can drive: deliver events, drop the connection, reconnect. */
export class FakeRunEventStream implements RunEventStream {
  subscriptions = 0;
  private onEvents: ((events: readonly RunEvent[]) => void) | null = null;
  private onConnectionChange: ((state: ConnectionState) => void) | null = null;

  subscribe(
    _runId: string,
    handlers: {
      onEvents: (events: readonly RunEvent[]) => void;
      onConnectionChange: (state: ConnectionState) => void;
    },
  ): RunSubscription {
    this.subscriptions += 1;
    this.onEvents = handlers.onEvents;
    this.onConnectionChange = handlers.onConnectionChange;
    handlers.onConnectionChange("live");
    return {
      close: () => {
        this.onEvents = null;
        this.onConnectionChange = null;
      },
    };
  }

  deliver(...events: RunEvent[]): void {
    this.onEvents?.(events);
  }

  setConnection(state: ConnectionState): void {
    this.onConnectionChange?.(state);
  }
}


export function makeMemoryStatus(overrides: Partial<MemoryStatus> = {}): MemoryStatus {
  return {
    projectId: "proj-1",
    environmentId: "default",
    graphAvailable: true,
    graphSchemaVersion: "roveqa.graph.v1",
    durableCandidates: 0,
    actionableCandidates: 0,
    syncPending: 0,
    syncFailed: 0,
    byStatus: {},
    ...overrides,
  };
}

export class FakeMemoryGateway implements MemoryGateway {
  private readonly value: MemoryStatus;

  constructor(value: MemoryStatus = makeMemoryStatus()) {
    this.value = value;
  }

  status(): Promise<MemoryStatus> {
    return Promise.resolve(this.value);
  }
}


export class FakeStoryGateway implements StoryGateway {
  readonly drafts: DraftStory[] = [];
  readonly compiled: string[] = [];
  stories: UserStory[];

  constructor(stories: UserStory[] = []) {
    this.stories = stories;
  }

  list(): Promise<UserStory[]> {
    return Promise.resolve(this.stories);
  }

  get(storyId: string): Promise<UserStory> {
    const found = this.stories.find((story) => story.storyId === storyId);
    if (found === undefined) return Promise.reject(new NotFound());
    return Promise.resolve(found);
  }

  create(draft: DraftStory): Promise<UserStory> {
    this.drafts.push(draft);
    const story: UserStory = {
      storyId: `story-${this.stories.length + 1}`,
      projectId: draft.projectId,
      actor: draft.actor,
      goal: draft.goal,
      acceptanceCriteria: draft.acceptanceCriteria,
    };
    this.stories = [...this.stories, story];
    return Promise.resolve(story);
  }

  compile(storyId: string, runPolicyId: string): Promise<CompiledPlan> {
    this.compiled.push(`${storyId}@${runPolicyId}`);
    return Promise.resolve({ planId: "plan-1", planVersion: "1" });
  }
}
