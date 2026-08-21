import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { useCreateProject, useProjectsViewModel } from "@viewmodels/projects/use-projects-viewmodel";
import { PlusIcon } from "@views/components/icons";
import {
  Badge,
  Button,
  Card,
  Field,
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
import { checkboxClass, inputClass } from "@views/components/form-classes";

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
      <PageTitle>Projects</PageTitle>
      <Lede>Every application this control plane knows how to test.</Lede>

      {isLoading ? <Notice>Loading projects…</Notice> : null}
      {error !== null ? <Notice tone="error">{error}</Notice> : null}

      {!isLoading && error === null && projects.length === 0 ? (
        <Notice>Nothing here yet. Add the first application below.</Notice>
      ) : null}

      {projects.length > 0 ? (
        <TableCard label="Projects">
          <TableHead>
            <Th>Project</Th>
            <Th>Id</Th>
            <Th>Can run</Th>
          </TableHead>
          <TableBody>
            {projects.map((project) => (
              <Tr key={project.projectId}>
                <Td>
                  <Link
                    className="font-semibold text-purple-600 hover:underline dark:text-purple-400"
                    to={`/projects/${project.projectId}`}
                  >
                    {project.name}
                  </Link>
                </Td>
                <Td className="font-mono text-xs text-gray-500 dark:text-gray-500">
                  {project.projectId}
                </Td>
                <Td>
                  {project.defaultRunPolicyId === null ? (
                    // Said on the row rather than discovered two screens later, where it
                    // reads as a broken control plane instead of a missing setting.
                    <Badge tone="unsure">no run policy</Badge>
                  ) : (
                    <Badge tone="pass">ready</Badge>
                  )}
                </Td>
              </Tr>
            ))}
          </TableBody>
        </TableCard>
      ) : null}

      {showForm ? (
        <Card className="mb-8">
          <SectionTitle>New project</SectionTitle>
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
            <Field label="Name" htmlFor="name" error={errors.name?.message}>
              <input
                id="name"
                className={inputClass(errors.name !== undefined)}
                {...register("name")}
                placeholder="Checkout"
              />
            </Field>

            <Field
              label="Application origin"
              htmlFor="origin"
              error={errors.origin?.message}
              hint="The only place that knows which application this tests. A run may go here and nowhere else, and the planner is told this address — without it a run starts on a blank page with nothing to aim at."
            >
              <input
                id="origin"
                className={inputClass(errors.origin !== undefined)}
                {...register("origin")}
                placeholder="http://localhost:3000"
              />
            </Field>

            <div className="mt-4">
              <label className="flex items-center text-sm text-gray-700 dark:text-gray-400">
                <input id="destructive" type="checkbox" className={checkboxClass()} {...register("destructiveActions")} />
                <span className="ml-2">Let runs click, type and submit</span>
              </label>
              <span className="mt-1 block text-xs text-gray-600 dark:text-gray-400">
                Off means the agent can look and never touch: every click is refused and the
                run ends. Leave it off against anything whose data you care about.
              </span>
            </div>

            <h4 className="mt-6 mb-2 text-sm font-semibold text-gray-600 dark:text-gray-300">
              What one run may spend
            </h4>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Actions" htmlFor="max-actions">
                <input
                  id="max-actions"
                  type="number"
                  className={inputClass()}
                  {...register("maxActions")}
                />
              </Field>
              <Field label="Model calls" htmlFor="max-model-calls">
                <input
                  id="max-model-calls"
                  type="number"
                  className={inputClass()}
                  {...register("maxModelCalls")}
                />
              </Field>
              <Field label="Seconds" htmlFor="max-duration">
                <input
                  id="max-duration"
                  type="number"
                  className={inputClass()}
                  {...register("maxDurationSeconds")}
                />
              </Field>
            </div>
            <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
              A run that hits one of these stops and reports <code>blocked</code>. It never
              reports a problem with the product it did not finish looking at.
            </p>

            <div className="mt-6 flex gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={creation.isCreating}>
                {creation.isCreating ? "Creating…" : "Create project"}
              </Button>
            </div>

            {creation.error !== null ? (
              <div className="mt-4">
                <Notice tone="error">{creation.error}</Notice>
              </div>
            ) : null}
          </form>
        </Card>
      ) : (
        <Button type="button" onClick={() => setShowForm(true)}>
          <PlusIcon className="mr-2 h-4 w-4" />
          New project
        </Button>
      )}
    </section>
  );
}
