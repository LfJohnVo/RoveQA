import { useParams } from "react-router";

import { useRunReportViewModel } from "@viewmodels/runs/use-run-report-viewmodel";
import { ConnectionIndicator } from "@views/components/connection-indicator";
import { FindingsList } from "@views/components/findings-list";
import { VerdictBadge } from "@views/components/verdict-badge";
import { useRunViewModel } from "@viewmodels/runs/use-run-viewmodel";

/**
 * The screen someone watches while a run happens.
 *
 * Renders and sends intents; it holds no logic about what a status permits. Whether
 * pause is available is a question about a run, answered in the domain, so this file
 * cannot get it subtly wrong in a way the tests would not see.
 */
export function RunPage() {
  const { runId = "" } = useParams();
  const run = useRunViewModel(runId);
  // Asked for only once the run has concluded something. A report fetched while the
  // run is still exploring would be empty and refetched on every status change.
  const report = useRunReportViewModel(runId, run.isTerminal);

  return (
    <section>
      <div className="run__header">
        <h2 className="page__title">Run</h2>
        <span className="run__id">{run.runId}</span>
        <span className="badge">{run.status}</span>
        {run.verdict !== null ? <VerdictBadge verdict={run.verdict} /> : null}
        <ConnectionIndicator state={run.connection} />
      </div>

      {run.isStale ? (
        <p className="notice" role="status">
          The live feed is not attached. What you see is the last durable state, and it
          will catch up on its own.
        </p>
      ) : null}

      {run.error !== null ? (
        <p className="notice notice--error" role="alert">
          {run.error}
        </p>
      ) : null}

      <div className="commands">
        <button className="button" type="button" onClick={run.pause} disabled={!run.canPause}>
          {run.pending === "pause" ? "Pausing…" : "Pause"}
        </button>
        <button className="button" type="button" onClick={run.resume} disabled={!run.canResume}>
          {run.pending === "resume" ? "Resuming…" : "Resume"}
        </button>
        <button
          className="button button--danger"
          type="button"
          onClick={run.cancel}
          disabled={!run.canCancel}
        >
          {run.pending === "cancel" ? "Cancelling…" : "Cancel"}
        </button>
      </div>

      {run.isTerminal ? (
        <>
          <h3 className="section__title">
            Findings
            {report.defects.length > 0 ? (
              <span className="card__meta">
                {report.defects.length} accusing the product
              </span>
            ) : null}
          </h3>
          {report.error !== null ? (
            <p className="notice notice--error" role="alert">
              {report.error}
            </p>
          ) : (
            <FindingsList findings={report.findings} />
          )}

          {report.artifacts.length > 0 ? (
            <>
              <h3 className="section__title">
                Evidence
                <span className="card__meta">{report.evidenceSetId}</span>
              </h3>
              <ul className="card-list">
                {report.artifacts.map((artifact) => (
                  <li className="card" key={artifact.artifactId}>
                    <span className="card__name">{artifact.kind}</span>{" "}
                    <span className="card__meta">
                      {artifact.relativePath} · {artifact.sizeBytes} bytes
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      ) : null}

      <h3 className="section__title">
        Timeline <span className="card__meta">{run.stepCount} events</span>
      </h3>

      <div className="timeline">
        {run.events.length === 0 ? (
          <p className="timeline__empty">
            {run.status === "loading" ? "Loading the run…" : "Nothing has happened yet."}
          </p>
        ) : (
          run.events.map((event) => (
            // Keyed by sequence, the durable log's own ordering. An array index would
            // reorder rows whenever a catch-up batch arrives out of order.
            <div className="timeline__row" key={event.sequence}>
              <span className="timeline__sequence">{event.sequence}</span>
              <span className="timeline__time">{formatTime(event.occurredAt)}</span>
              <span className="timeline__type">{event.type}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function formatTime(iso: string): string {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? iso : at.toLocaleTimeString();
}
