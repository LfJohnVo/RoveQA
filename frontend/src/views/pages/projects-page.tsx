import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { useCreateProject, useProjectsViewModel } from "@viewmodels/projects/use-projects-viewmodel";

/**
 * Every project, and the way in.
 *
 * The form makes the policy part of creating a project rather than a later step,
 * because a project without one cannot compile a plan or start a run: it would list
 * here, open, and refuse to do anything. The two fields that decide what a run may do
 * — where it may go, and whether it may click — are asked here for the same reason,
 * while there is still nothing to break.
 */
const schema = z.object({
  name: z.string().trim().min(1, "give it a name"),
  origin: z
    .string()
    .trim()
    .min(1, "which application?")
    .refine(
      (value) => /^https?:\/\/[^/\s]+$/.test(value),
      "an origin is scheme, host and port — no path, e.g. http://localhost:3000",
    ),
  maxActions: z.coerce.number().int().min(1).max(10_000),
  maxModelCalls: z.coerce.number().int().min(0).max(10_000),
  maxDurationSeconds: z.coerce.number().int().min(1).max(172_800),
  destructiveActions: z.boolean(),
});

type FormValues = z.input<typeof schema>;

const DEFAULTS: FormValues = {
  name: "",
  origin: "",
  maxActions: 20,
  maxModelCalls: 20,
  maxDurationSeconds: 300,
  destructiveActions: false,
};

export function ProjectsPage() {
  const { projects, isLoading, error } = useProjectsViewModel();
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const creation = useCreateProject((project) => {
    void navigate(`/projects/${project.projectId}`);
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: DEFAULTS });

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
        <p className="notice">Nothing here yet. Add the first application below.</p>
      ) : null}

      <ul className="card-list">
        {projects.map((project) => (
          <li key={project.projectId}>
            <Link className="card" to={`/projects/${project.projectId}`}>
              <div className="card__name">{project.name}</div>
              <div className="card__meta">
                {project.defaultRunPolicyId === null ? (
                  <span className="card__warning">no run policy — cannot start a run</span>
                ) : (
                  project.projectId
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {showForm ? (
        <>
          <h3 className="section__title">New project</h3>
          <form
            onSubmit={(event) =>
              void handleSubmit((values) =>
                creation.create({
                  name: values.name,
                  allowedOrigins: [values.origin],
                  maxActions: Number(values.maxActions),
                  maxModelCalls: Number(values.maxModelCalls),
                  maxDurationSeconds: Number(values.maxDurationSeconds),
                  destructiveActions: values.destructiveActions,
                }),
              )(event)
            }
          >
            <div className="field">
              <label htmlFor="name">Name</label>
              <input id="name" {...register("name")} placeholder="Checkout" />
              {errors.name ? <span className="field__error">{errors.name.message}</span> : null}
            </div>

            <div className="field">
              <label htmlFor="origin">Application origin</label>
              <input id="origin" {...register("origin")} placeholder="http://localhost:3000" />
              <span className="field__note">
                The only place that knows which application this tests. A run may go here
                and nowhere else, and the planner is told this address — without it a run
                starts on a blank page with nothing to aim at.
              </span>
              {errors.origin ? <span className="field__error">{errors.origin.message}</span> : null}
            </div>

            <div className="field field--inline">
              <label htmlFor="destructive">
                <input id="destructive" type="checkbox" {...register("destructiveActions")} />
                Let runs click, type and submit
              </label>
              <span className="field__note">
                Off means the agent can look and never touch: every click is refused and
                the run ends. Leave it off against anything whose data you care about.
              </span>
            </div>

            <h4 className="section__title">What one run may spend</h4>
            <div className="field">
              <label htmlFor="max-actions">Actions</label>
              <input id="max-actions" type="number" {...register("maxActions")} />
            </div>
            <div className="field">
              <label htmlFor="max-model-calls">Model calls</label>
              <input id="max-model-calls" type="number" {...register("maxModelCalls")} />
            </div>
            <div className="field">
              <label htmlFor="max-duration">Seconds</label>
              <input id="max-duration" type="number" {...register("maxDurationSeconds")} />
              <span className="field__note">
                A run that hits one of these stops and reports <code>blocked</code>. It
                never reports a problem with the product it did not finish looking at.
              </span>
            </div>

            <div className="commands">
              <button className="button" type="button" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button
                className="button button--primary"
                type="submit"
                disabled={creation.isCreating}
              >
                {creation.isCreating ? "Creating…" : "Create project"}
              </button>
            </div>

            {creation.error !== null ? (
              <p className="notice notice--error" role="alert">
                {creation.error}
              </p>
            ) : null}
          </form>
        </>
      ) : (
        <div className="commands">
          <button className="button button--primary" type="button" onClick={() => setShowForm(true)}>
            New project
          </button>
        </div>
      )}
    </section>
  );
}
