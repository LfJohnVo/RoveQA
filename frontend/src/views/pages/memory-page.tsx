import { useParams } from "react-router";

import { useMemoryViewModel } from "@viewmodels/knowledge/use-memory-viewmodel";
import { Card, Lede, Notice, PageTitle, SectionTitle, StatCard } from "@views/components/ui";

/**
 * What this project has learned.
 *
 * Written to make one distinction unmissable: durable knowledge and the graph
 * projection are different things. A graph that is down or behind is a slower next
 * run, not lost memory, and a screen that blurred the two would send someone chasing
 * a data-loss incident that did not happen.
 */
export function MemoryPage() {
  const { projectId = "" } = useParams();
  const memory = useMemoryViewModel(projectId);

  if (memory.isLoading) return <Notice>Loading memory…</Notice>;
  if (memory.error !== null || memory.status === null) {
    return <Notice tone="error">{memory.error ?? "the control plane did not answer"}</Notice>;
  }

  const status = memory.status;
  const learnedNothing = Object.values(status.byStatus).every((total) => total === 0);

  return (
    <section>
      <PageTitle>Learned memory</PageTitle>
      <Lede>
        What earlier verified runs established about this application. Knowledge lives in
        PostgreSQL; the graph is a projection of it that can be rebuilt at any time.
      </Lede>

      <div className="mb-8 grid gap-6 md:grid-cols-3">
        <StatCard label="Durable knowledge" value={status.durableCandidates} tone="purple" />
        <StatCard label="Usable by a planner" value={status.actionableCandidates} tone="blue" />
        <StatCard
          label="Graph"
          value={status.graphAvailable ? "available" : "unavailable"}
          tone={status.graphAvailable ? "green" : "yellow"}
        />
      </div>

      {!status.graphAvailable ? (
        <Notice tone="warning">
          The graph is unreachable. Nothing has been lost — memory is served from
          PostgreSQL and the projection rebuilds from it.
        </Notice>
      ) : null}

      {memory.graphIsBehind ? (
        <Notice tone="warning">
          {status.syncPending} waiting and {status.syncFailed} failed to project. The
          backlog kept the work; runs stay correct while it drains.
        </Notice>
      ) : null}

      <SectionTitle>By status</SectionTitle>
      {learnedNothing ? (
        <Notice>
          Nothing learned yet. Knowledge appears once two independent runs agree — one run
          is a coincidence.
        </Notice>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(status.byStatus)
            .filter(([, total]) => total > 0)
            .map(([name, total]) => (
              <Card key={name}>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{name}</p>
                <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{total}</p>
              </Card>
            ))}
        </div>
      )}
    </section>
  );
}
