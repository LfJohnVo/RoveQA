import { useParams } from "react-router";

import { useMemoryViewModel } from "@viewmodels/knowledge/use-memory-viewmodel";

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

  if (memory.isLoading) return <p className="notice">Loading memory…</p>;
  if (memory.error !== null || memory.status === null) {
    return (
      <p className="notice notice--error" role="alert">
        {memory.error ?? "the control plane did not answer"}
      </p>
    );
  }

  const status = memory.status;

  return (
    <section>
      <h2 className="page__title">Learned memory</h2>
      <p className="page__lede">
        What earlier verified runs established about this application. Knowledge lives in
        PostgreSQL; the graph is a projection of it that can be rebuilt at any time.
      </p>

      <dl className="stats">
        <div className="stat">
          <dt>Durable knowledge</dt>
          <dd>{status.durableCandidates}</dd>
        </div>
        <div className="stat">
          <dt>Usable by a planner</dt>
          <dd>{status.actionableCandidates}</dd>
        </div>
        <div className="stat">
          <dt>Graph</dt>
          <dd className={status.graphAvailable ? "" : "stat--warn"}>
            {status.graphAvailable ? "available" : "unavailable"}
          </dd>
        </div>
      </dl>

      {!status.graphAvailable ? (
        <p className="notice" role="status">
          The graph is unreachable. Nothing has been lost — memory is served from
          PostgreSQL and the projection rebuilds from it.
        </p>
      ) : null}

      {memory.graphIsBehind ? (
        <p className="notice" role="status">
          {status.syncPending} waiting and {status.syncFailed} failed to project. The
          backlog kept the work; runs stay correct while it drains.
        </p>
      ) : null}

      <h3 className="page__title" style={{ fontSize: "var(--text-lg)" }}>
        By status
      </h3>
      <ul className="card-list">
        {Object.entries(status.byStatus)
          .filter(([, total]) => total > 0)
          .map(([name, total]) => (
            <li className="card" key={name}>
              <span className="card__name">{name}</span> <span className="card__meta">{total}</span>
            </li>
          ))}
      </ul>
      {Object.values(status.byStatus).every((total) => total === 0) ? (
        <p className="notice">
          Nothing learned yet. Knowledge appears once two independent runs agree — one
          run is a coincidence.
        </p>
      ) : null}
    </section>
  );
}
