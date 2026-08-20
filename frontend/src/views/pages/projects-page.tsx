import { Link } from "react-router";

import { useProjectsViewModel } from "@viewmodels/projects/use-projects-viewmodel";

export function ProjectsPage() {
  const { projects, isLoading, error } = useProjectsViewModel();

  return (
    <section>
      <h2 className="page__title">Projects</h2>
      <p className="page__lede">Every application this control plane knows how to test.</p>

      {isLoading ? <p className="notice">Loading projects…</p> : null}
      {error !== null ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && error === null && projects.length === 0 ? (
        <p className="notice">
          No projects yet. Create one with <code>roveqa setup</code> or the API.
        </p>
      ) : null}

      <ul className="card-list">
        {projects.map((project) => (
          <li key={project.projectId}>
            <Link className="card" to={`/projects/${project.projectId}`}>
              <div className="card__name">{project.name}</div>
              <div className="card__meta">{project.projectId}</div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
