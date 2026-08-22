/**
 * A project's runs, newest first.
 *
 * The screen this feeds is the only way into a run that this tab did not start. Before
 * it existed the console could show the run it had just launched and nothing else:
 * every run from a schedule, from the CLI, or from yesterday had a report sitting in
 * the database and no route to it.
 */

import { useQuery } from "@tanstack/react-query";

import type { Run } from "@domain/runs/run";
import { isActive } from "@domain/runs/run";
import { useGateways } from "@viewmodels/gateways-context";

const DEFAULT_LIMIT = 50;

const ACTIVE_REFETCH_MS = 5_000;

export interface ProjectRunsViewModel {
  runs: readonly Run[];
  isLoading: boolean;
  error: string | null;
}

export function useProjectRunsViewModel(
  projectId: string,
  limit = DEFAULT_LIMIT,
): ProjectRunsViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["project-runs", projectId, limit],
    queryFn: () => gateways.runs.listForProject(projectId, limit),
    // Polled only while something is still going. A run's own page has the socket; this
    // is a list, and a list of finished runs does not change on its own — refetching it
    // forever would be a request every five seconds for a page nobody is watching.
    refetchInterval: (query) =>
      (query.state.data ?? []).some(isActive) ? ACTIVE_REFETCH_MS : false,
  });

  return {
    runs: query.data ?? [],
    isLoading: query.isPending,
    error: query.error === null ? null : messageFor(query.error),
  };
}

function messageFor(cause: unknown): string {
  return cause instanceof Error ? cause.message : "the control plane did not answer";
}
