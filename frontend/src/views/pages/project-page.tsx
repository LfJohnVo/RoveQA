import { Link, useParams } from "react-router";

import type { Run } from "@domain/runs/run";
import { useProjectRunsViewModel } from "@viewmodels/runs/use-project-runs-viewmodel";
import { useSessionsViewModel } from "@viewmodels/projects/use-sessions-viewmodel";
import { useProjectViewModel } from "@viewmodels/projects/use-projects-viewmodel";
import { MemoryIcon, RunIcon, StoriesIcon } from "@views/components/icons";
import { VerdictBadge } from "@views/components/verdict-badge";
import {
  Badge,
  Button,
  Card,
  Lede,
  Notice,
  PageTitle,
  SectionTitle,
  TableBody,
  TableCard,
  TableHead,
  Td,
  Th,
  Tr,
} from "@views/components/ui";

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const { project, isLoading, notFound, error } = useProjectViewModel(projectId);

  if (isLoading) return <Notice>Loading…</Notice>;

  // A wrong URL and a broken control plane are different problems and get different
  // screens: one is the reader's mistake to fix, the other is not.
  if (notFound) {
    return (
      <section>
        <PageTitle>No such project</PageTitle>
        <Lede>
          Nothing here answers to{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs dark:bg-gray-700">
            {projectId}
          </code>
          .
        </Lede>
        <Link
          className="inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:border-gray-500 dark:border-gray-600 dark:text-gray-400"
          to="/projects"
        >
          Back to projects
        </Link>
      </section>
    );
  }

  if (error !== null || project === null) {
    return <Notice tone="error">{error ?? "the control plane did not answer"}</Notice>;
  }

  const cannotRun = project.defaultRunPolicyId === null;

  return (
    <section>
      <PageTitle>{project.name}</PageTitle>
      <p className="-mt-4 mb-6 font-mono text-xs text-gray-500 dark:text-gray-500">
        {project.projectId}
      </p>

      {cannotRun ? (
        <Notice tone="warning">
          No default run policy. A run cannot start until one exists — the policy is what
          says where a run may go and what it may do there.
        </Notice>
      ) : null}

      <div className="grid gap-6 md:grid-cols-3">
        <Link
          to={`/projects/${project.projectId}/runs/new`}
          className="rounded-lg focus:shadow-outline-purple focus:outline-none"
        >
          <Card className="flex h-full items-center">
            <div className="mr-4 rounded-full bg-purple-100 p-3 text-purple-500 dark:bg-purple-500 dark:text-purple-100">
              <RunIcon />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">Start a run</p>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Against a compiled plan
              </p>
            </div>
          </Card>
        </Link>

        <Link
          to={`/projects/${project.projectId}/stories`}
          className="rounded-lg focus:shadow-outline-purple focus:outline-none"
        >
          <Card className="flex h-full items-center">
            <div className="mr-4 rounded-full bg-blue-100 p-3 text-blue-500 dark:bg-blue-500 dark:text-blue-100">
              <StoriesIcon />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">Stories</p>
              <p className="text-xs text-gray-600 dark:text-gray-400">Write one, compile a plan</p>
            </div>
          </Card>
        </Link>

        <Link
          to={`/projects/${project.projectId}/memory`}
          className="rounded-lg focus:shadow-outline-purple focus:outline-none"
        >
          <Card className="flex h-full items-center">
            <div className="mr-4 rounded-full bg-green-100 p-3 text-green-500 dark:bg-green-500 dark:text-green-100">
              <MemoryIcon />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                Learned memory
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                What verified runs taught it
              </p>
            </div>
          </Card>
        </Link>
      </div>

      {cannotRun ? null : (
        <p className="mt-6 text-xs text-gray-500 dark:text-gray-500">
          Default policy{" "}
          <span className="font-mono">{project.defaultRunPolicyId}</span>
        </p>
      )}

      <Sessions projectId={project.projectId} />
      <RunHistory projectId={project.projectId} />
    </section>
  );
}

/**
 * Which environments this project has, and what each would lend a run.
 *
 * Read and revoke only. Registering a session is `roveqa session register <file>` on
 * purpose: a paste box would route a credential through browser memory, autofill and
 * anything that screenshots the tab, and buy nothing (ADR 0019).
 */
function Sessions({ projectId }: { projectId: string }) {
  const { environments, isLoading, error, revoke, isRevoking, revokeError } =
    useSessionsViewModel(projectId);

  if (isLoading) return null;
  if (error !== null) {
    return (
      <section className="mt-8">
        <SectionTitle>Sessions</SectionTitle>
        <Notice tone="error">{error}</Notice>
      </section>
    );
  }
  if (environments.length === 0) {
    // No environments is the ordinary shape for a project testing a public site, so it
    // says what that means rather than showing an empty table that looks like a failure.
    return (
      <section className="mt-8">
        <SectionTitle>Sessions</SectionTitle>
        <Notice>
          No environments yet. Runs go out anonymous, which is all a public site needs.
        </Notice>
      </section>
    );
  }

  return (
    <section className="mt-8">
      <SectionTitle>Sessions</SectionTitle>
      {revokeError !== null ? <Notice tone="error">{revokeError}</Notice> : null}
      <TableCard label="Sessions">
        <TableHead>
          <Th>Environment</Th>
          <Th>Session</Th>
          <Th>Valid until</Th>
          <Th>Established</Th>
          <Th> </Th>
        </TableHead>
        <TableBody>
          {environments.map(({ environment, current, expired }) => (
            <Tr key={environment.environmentId}>
              <Td>{environment.name}</Td>
              <Td>
                {current === null ? (
                  <Badge tone="neutral">anonymous</Badge>
                ) : (
                  <span className="font-semibold">{current.label}</span>
                )}
              </Td>
              <Td className="text-xs text-gray-600 dark:text-gray-400">
                {current === null ? "—" : validity(current.validUntil, expired)}
              </Td>
              <Td className="text-xs text-gray-600 dark:text-gray-400">
                {current === null ? "—" : current.establishedBy || "not recorded"}
              </Td>
              <Td>
                {current === null ? null : (
                  <Button
                    variant="danger"
                    type="button"
                    disabled={isRevoking}
                    onClick={() => revoke(environment.environmentId, current.sessionId)}
                  >
                    Revoke
                  </Button>
                )}
              </Td>
            </Tr>
          ))}
        </TableBody>
      </TableCard>
      <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
        Revoking destroys the key. The record stays as the audit trail, and restoring a
        backup will not bring the session back. Register one with{" "}
        <code className="rounded bg-gray-100 px-1 py-0.5 font-mono dark:bg-gray-700">
          roveqa session register
        </code>
        .
      </p>
    </section>
  );
}

function validity(validUntil: string | null, expired: boolean) {
  // "Nobody said" and "it is over" are different facts. Rendering the first as the
  // second would show a working session in the colour of a broken one.
  if (validUntil === null) return "no stated expiry";
  return expired ? <span className="font-semibold text-red-600">expired</span> : validUntil;
}

/**
 * Every run of this project, newest first.
 *
 * The way into a report the console did not start. Until this existed a run was
 * reachable only while its page stayed open, which made the whole interface a viewer of
 * work you had to launch somewhere else and then not navigate away from.
 */
function RunHistory({ projectId }: { projectId: string }) {
  const { runs, isLoading, error } = useProjectRunsViewModel(projectId);

  return (
    <section className="mt-8">
      <SectionTitle>Runs</SectionTitle>

      {isLoading ? <Notice>Loading runs…</Notice> : null}
      {error !== null ? <Notice tone="error">{error}</Notice> : null}

      {!isLoading && error === null && runs.length === 0 ? (
        <Notice>No runs yet. Start one above and its report will appear here.</Notice>
      ) : null}

      {runs.length > 0 ? (
        <TableCard label="Runs">
          <TableHead>
            <Th>Run</Th>
            <Th>Status</Th>
            <Th>Verdict</Th>
            <Th>Plan</Th>
          </TableHead>
          <TableBody>
            {runs.map((run) => (
              <Tr key={run.runId}>
                <Td>
                  <Link
                    className="font-mono text-xs font-semibold text-purple-600 hover:underline dark:text-purple-400"
                    to={`/runs/${run.runId}`}
                  >
                    {run.runId}
                  </Link>
                </Td>
                <Td className="text-xs text-gray-600 dark:text-gray-400">{run.status}</Td>
                <Td>
                  {run.verdict === null ? (
                    // Not a verdict of "unknown": a run still going has not concluded
                    // anything, and a badge would report the absence of an answer as one.
                    <span className="text-xs text-gray-500 dark:text-gray-500">—</span>
                  ) : (
                    <VerdictBadge verdict={run.verdict} />
                  )}
                </Td>
                <Td>{planLabel(run)}</Td>
              </Tr>
            ))}
          </TableBody>
        </TableCard>
      ) : null}
    </section>
  );
}

function planLabel(run: Run) {
  if (run.planId === null) {
    // A run with no plan explored. Said plainly rather than left blank, because blank
    // reads as missing data about a run whose shape is deliberate (ADR 0017).
    return <Badge tone="neutral">exploration</Badge>;
  }
  return (
    <span className="font-mono text-xs text-gray-500 dark:text-gray-500">
      {run.planId.slice(0, 8)} v{run.planVersion}
    </span>
  );
}
