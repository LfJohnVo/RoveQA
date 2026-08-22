/**
 * What a traversal mapped, for the run that made it.
 *
 * A run that never explored has no map, and that is a fact about the run rather than a
 * failure to read one — so `absent` is a first-class answer here and not an error. A red
 * banner on every planned run's page would train people to ignore red banners.
 */

import { useQuery } from "@tanstack/react-query";

import type { ExplorationMap } from "@domain/runs/exploration";
import { useGateways } from "@viewmodels/gateways-context";

export interface ExplorationViewModel {
  map: ExplorationMap | null;
  /** True when the run simply did not explore. Distinguished from "not loaded yet". */
  absent: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useExplorationViewModel(runId: string, enabled: boolean): ExplorationViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["exploration", runId],
    queryFn: () => gateways.runs.exploration(runId),
    // Asked for once the run has concluded. A map read mid-crawl is a picture of a
    // moment, and refetching it on every status change would cost more than it says.
    enabled,
  });

  return {
    map: query.data ?? null,
    absent: query.isSuccess && query.data === null,
    isLoading: enabled && query.isPending,
    error: query.error === null ? null : messageFor(query.error),
  };
}

function messageFor(cause: unknown): string {
  return cause instanceof Error ? cause.message : "the map could not be read";
}
