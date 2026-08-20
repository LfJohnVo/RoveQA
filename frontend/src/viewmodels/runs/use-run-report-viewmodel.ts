/**
 * What the run concluded, and the evidence for it.
 *
 * Kept apart from the run's live state: findings are settled facts read once a run has
 * something to say, while status changes by the second. Folding them into one query
 * would refetch the whole report on every status change for no gain.
 */

import { useQuery } from "@tanstack/react-query";

import { defects, unresolved, type Artifact, type Finding } from "@domain/runs/findings";
import { useGateways } from "@viewmodels/gateways-context";

export interface RunReportViewModel {
  findings: readonly Finding[];
  /** Findings that accuse the product. Only `product` failures qualify — a plan that
   * could not be verified is a failure of the run, not of what it tested. */
  defects: readonly Finding[];
  unresolved: readonly Finding[];
  artifacts: readonly Artifact[];
  evidenceSetId: string | null;
  isLoading: boolean;
  error: string | null;
}

export function useRunReportViewModel(runId: string, enabled: boolean): RunReportViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["run-report", runId],
    queryFn: () => gateways.runs.report(runId),
    // Asked only once the run has concluded something. Polling a report that cannot
    // have changed is load with no answer attached.
    enabled,
  });

  const findings = query.data?.findings ?? [];
  return {
    findings,
    defects: defects(findings),
    unresolved: unresolved(findings),
    artifacts: query.data?.artifacts ?? [],
    evidenceSetId: query.data?.evidenceSetId ?? null,
    isLoading: enabled && query.isPending,
    error: query.error === null ? null : messageFor(query.error),
  };
}

function messageFor(cause: unknown): string {
  return cause instanceof Error ? cause.message : "the report could not be read";
}
