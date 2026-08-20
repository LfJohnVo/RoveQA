/**
 * Learned memory, as a human needs to read it.
 *
 * The distinction this file protects is the same one the backend defends everywhere:
 * **an observation and a hypothesis are different claims.** A browser that renders
 * them identically would undo, at the last step, the labelling the whole knowledge
 * pipeline carries — so `observed` and `modelDerived` travel all the way here and the
 * UI is built to show them.
 */

export type CandidateStatus =
  | "candidate"
  | "promoted"
  | "trusted"
  | "invalidated"
  | "rejected"
  | "pending_sync";

export interface MemoryStatus {
  projectId: string;
  environmentId: string;
  graphAvailable: boolean;
  graphSchemaVersion: string;
  durableCandidates: number;
  /** What a planner could be offered right now. Survives losing the graph entirely. */
  actionableCandidates: number;
  syncPending: number;
  syncFailed: number;
  byStatus: Readonly<Record<string, number>>;
}

/** True when the projection is behind what PostgreSQL holds. Not an error: the durable
 * side is intact and the backlog will drain. */
export function graphIsBehind(status: MemoryStatus): boolean {
  return status.syncPending > 0 || status.syncFailed > 0;
}

/** How much of what this project learned is usable today. */
export function actionableShare(status: MemoryStatus): number {
  return status.durableCandidates === 0
    ? 0
    : status.actionableCandidates / status.durableCandidates;
}
