/**
 * What a project has learned, for the knowledge browser.
 *
 * The two numbers are kept apart on purpose: how much knowledge exists, and how much
 * of it the graph currently holds. One combined number could not say "the projection
 * is empty but nothing was lost", which is the state an operator most needs to
 * recognise — it is a performance problem, not a data one.
 */

import { useQuery } from "@tanstack/react-query";

import { actionableShare, graphIsBehind, type MemoryStatus } from "@domain/knowledge/memory";
import { useGateways } from "@viewmodels/gateways-context";

export interface MemoryViewModel {
  status: MemoryStatus | null;
  isLoading: boolean;
  error: string | null;
  /** The projection is behind. Worth saying; not worth alarming about. */
  graphIsBehind: boolean;
  actionableShare: number;
}

export function useMemoryViewModel(projectId: string, environmentId = "default"): MemoryViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["memory", projectId, environmentId],
    queryFn: () => gateways.memory.status(projectId, environmentId),
    // Sync lag moves on its own as the backlog drains, so this is one of the few
    // screens where polling tells the truth better than a stale cache.
    refetchInterval: 10_000,
  });

  const status = query.data ?? null;
  return {
    status,
    isLoading: query.isPending,
    error: query.error === null ? null : messageFor(query.error),
    graphIsBehind: status !== null && graphIsBehind(status),
    actionableShare: status === null ? 0 : actionableShare(status),
  };
}

function messageFor(cause: unknown): string {
  return cause instanceof Error ? cause.message : "the control plane did not answer";
}
