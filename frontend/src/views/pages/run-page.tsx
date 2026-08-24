import { useParams } from "react-router";

import { useRunReportViewModel } from "@viewmodels/runs/use-run-report-viewmodel";
import { ConnectionIndicator } from "@views/components/connection-indicator";
import { FindingsList } from "@views/components/findings-list";
import { VerdictBadge } from "@views/components/verdict-badge";
import { useExplorationViewModel } from "@viewmodels/runs/use-exploration-viewmodel";
import { useRunViewModel } from "@viewmodels/runs/use-run-viewmodel";
import { StateMap } from "@views/components/state-map";
import {
  Badge,
  Button,
  Notice,
  SectionTitle,
  TableBody,
  TableCard,
  TableHead,
  Td,
  Th,
  Tr,
} from "@views/components/ui";

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
  const exploration = useExplorationViewModel(runId, run.isTerminal);

  return (
    <section>
      <div className="mt-6 mb-6 flex flex-wrap items-center gap-3">
        <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-200">Run</h2>
        <span className="font-mono text-xs text-gray-500 dark:text-gray-500">{run.runId}</span>
        <Badge tone="neutral">{run.status}</Badge>
        {run.verdict !== null ? <VerdictBadge verdict={run.verdict} /> : null}
        <span className="ml-auto">
          <ConnectionIndicator state={run.connection} />
        </span>
      </div>

      {run.isStale ? (
        <Notice tone="warning">
          The live feed is not attached. What you see is the last durable state, and it will
          catch up on its own.
        </Notice>
      ) : null}

      {run.error !== null ? <Notice tone="error">{run.error}</Notice> : null}

      <div className="mb-8 flex flex-wrap gap-3">
        <Button variant="secondary" type="button" onClick={run.pause} disabled={!run.canPause}>
          {run.pending === "pause" ? "Pausing…" : "Pause"}
        </Button>
        <Button variant="secondary" type="button" onClick={run.resume} disabled={!run.canResume}>
          {run.pending === "resume" ? "Resuming…" : "Resume"}
        </Button>
        <Button variant="danger" type="button" onClick={run.cancel} disabled={!run.canCancel}>
          {run.pending === "cancel" ? "Cancelling…" : "Cancel"}
        </Button>
      </div>

      {run.isTerminal ? (
        <>
          <div className="flex items-baseline gap-3">
            <SectionTitle>Findings</SectionTitle>
            {report.defects.length > 0 ? (
              // The one count worth putting in red: everything else a run reports is the
              // run talking about itself.
              <span className="mb-4 text-xs font-semibold text-red-600 dark:text-red-400">
                {report.defects.length} accusing the product
              </span>
            ) : null}
          </div>
          {report.error !== null ? (
            <Notice tone="error">{report.error}</Notice>
          ) : (
            <div className="mb-8">
              <FindingsList findings={report.findings} />
            </div>
          )}

          {report.observed.length > 0 ? (
            <>
              <SectionTitle>What the browser saw</SectionTitle>
              <p className="-mt-2 mb-4 text-xs text-gray-600 dark:text-gray-400">
                Console errors and requests that never completed. Nobody asked about
                these and the browser saw them anyway — none of them is a verdict about
                the application.
              </p>
              <TableCard label="What the browser saw">
                <TableHead>
                  <Th>Kind</Th>
                  <Th>Detail</Th>
                  <Th>Episode</Th>
                </TableHead>
                <TableBody>
                  {report.observed.map((failure, index) => (
                    // Keyed by position: two identical console errors from two episodes
                    // are two observations, and deduplicating them here would hide that
                    // the second episode saw it too.
                    <Tr key={`${failure.kind}-${index}`}>
                      <Td>
                        <Badge tone="unsure">{failure.kind.replace("_", " ")}</Badge>
                      </Td>
                      <Td className="font-mono text-xs whitespace-normal break-all">
                        {failure.detail}
                      </Td>
                      <Td className="tabular-nums">{failure.episodeIndex}</Td>
                    </Tr>
                  ))}
                </TableBody>
              </TableCard>
            </>
          ) : null}

          {report.artifacts.length > 0 ? (
            <>
              <div className="flex items-baseline gap-3">
                <SectionTitle>Evidence</SectionTitle>
                <span className="mb-4 font-mono text-xs text-gray-500 dark:text-gray-500">
                  {report.evidenceSetId}
                </span>
              </div>
              <TableCard label="Evidence">
                <TableHead>
                  <Th>Kind</Th>
                  <Th>Path</Th>
                  <Th>Size</Th>
                </TableHead>
                <TableBody>
                  {report.artifacts.map((artifact) => (
                    <Tr key={artifact.artifactId}>
                      <Td className="font-semibold">{artifact.kind}</Td>
                      <Td className="font-mono text-xs">{artifact.relativePath}</Td>
                      <Td className="tabular-nums">{artifact.sizeBytes} bytes</Td>
                    </Tr>
                  ))}
                </TableBody>
              </TableCard>
            </>
          ) : null}
        </>
      ) : null}

      {exploration.map !== null ? (
        <>
          <div className="flex flex-wrap items-baseline gap-3">
            <SectionTitle>What it mapped</SectionTitle>
            <span className="mb-4 text-xs text-gray-500 dark:text-gray-500">
              {exploration.map.statesDiscovered} states · {exploration.map.actionsTaken} actions
              {exploration.map.declined > 0
                ? ` · ${exploration.map.declined} controls left alone`
                : ""}
            </span>
          </div>

          {exploration.map.complete ? null : (
            // The difference between "this is the application" and "this is as far as it
            // got". A map with holes read as a complete one is how a page that vanished
            // gets reported as removed.
            <Notice tone="warning">
              The crawl stopped on <code>{exploration.map.stopReason ?? "a budget"}</code>, so
              this is what it reached rather than everything there is.
            </Notice>
          )}

          <StateMap states={exploration.map.states} />
        </>
      ) : null}

      <div className="flex items-baseline gap-3">
        <SectionTitle>Timeline</SectionTitle>
        <span className="mb-4 text-xs text-gray-500 dark:text-gray-500">
          {run.stepCount} events
        </span>
      </div>

      {run.events.length === 0 ? (
        <Notice>
          {run.status === "loading" ? "Loading the run…" : "Nothing has happened yet."}
        </Notice>
      ) : (
        <TableCard label="Timeline">
          <TableHead>
            <Th>#</Th>
            <Th>Time</Th>
            <Th>Event</Th>
          </TableHead>
          <TableBody>
            {run.events.map((event) => (
              // Keyed by sequence, the durable log's own ordering. An array index would
              // reorder rows whenever a catch-up batch arrives out of order.
              <Tr key={event.sequence}>
                <Td className="tabular-nums text-gray-500 dark:text-gray-500">
                  {event.sequence}
                </Td>
                <Td className="tabular-nums">{formatTime(event.occurredAt)}</Td>
                <Td className="font-mono text-xs">{event.type}</Td>
              </Tr>
            ))}
          </TableBody>
        </TableCard>
      )}
    </section>
  );
}

function formatTime(iso: string): string {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? iso : at.toLocaleTimeString();
}
