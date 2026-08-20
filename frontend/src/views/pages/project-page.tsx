import { Link, useParams } from "react-router";

import { useProjectViewModel } from "@viewmodels/projects/use-projects-viewmodel";

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const { project, isLoading, notFound, error } = useProjectViewModel(projectId);

  if (isLoading) return <p className="notice">Loading…</p>;

  // A wrong URL and a broken control plane are different problems and get different
  // screens: one is the reader's mistake to fix, the other is not.
  if (notFound) {
    return (
      <section>
        <h2 className="page__title">No such project</h2>
        <p className="page__lede">
          Nothing here answers to <code>{projectId}</code>.
        </p>
        <Link className="button" to="/projects">
          Back to projects
        </Link>
      </section>
    );
  }

  if (error !== null || project === null) {
    return (
      <p className="notice notice--error" role="alert">
        {error ?? "the control plane did not answer"}
      </p>
    );
  }

  return (
    <section>
      <h2 className="page__title">{project.name}</h2>
      <p className="card__meta">{project.projectId}</p>
      <p className="page__lede">
        {project.defaultRunPolicyId === null
          ? "No default run policy. A run cannot start until one exists."
          : `Default policy ${project.defaultRunPolicyId}`}
      </p>
      <div className="commands">
        <Link className="button button--primary" to={`/projects/${project.projectId}/runs/new`}>
          Start a run
        </Link>
        <Link className="button" to={`/projects/${project.projectId}/stories`}>
          Stories
        </Link>
        <Link className="button" to={`/projects/${project.projectId}/memory`}>
          Learned memory
        </Link>
      </div>
    </section>
  );
}
