import { Link, useParams } from "react-router";

import { useProjectViewModel } from "@viewmodels/projects/use-projects-viewmodel";
import { MemoryIcon, RunIcon, StoriesIcon } from "@views/components/icons";
import { Card, Lede, Notice, PageTitle } from "@views/components/ui";

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
    </section>
  );
}
