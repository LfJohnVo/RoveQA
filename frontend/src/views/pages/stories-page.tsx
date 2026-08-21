import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { useNavigate, useParams } from "react-router";
import { z } from "zod";

import { isFullyModelJudged, unverifiable } from "@domain/qa/story";
import { useGateways } from "@viewmodels/gateways-context";
import { useProjectViewModel } from "@viewmodels/projects/use-projects-viewmodel";
import {
  Button,
  Card,
  Field,
  Lede,
  Notice,
  PageTitle,
  SectionTitle,
} from "@views/components/ui";
import { inputClass } from "@views/components/form-classes";

/**
 * Writing a story, and compiling it into a plan.
 *
 * The screen is built around one trade the author is making without realising it: a
 * criterion with a verification hint gets a deterministic check and can accuse the
 * product; one without is judged by a model, and a run resting on it ends
 * `inconclusive` (docs/00). Told here, while it can still be changed, rather than
 * discovered in a report three runs later.
 */
const schema = z.object({
  actor: z.string().trim().min(1, "who is doing this?"),
  goal: z.string().trim().min(1, "what are they trying to achieve?"),
  criteria: z
    .array(
      z.object({
        criterionId: z
          .string()
          .trim()
          .min(1, "an id the report can point at")
          .regex(/^[a-z0-9][a-z0-9-]*$/, "lowercase letters, digits and dashes"),
        description: z.string().trim().min(1, "what has to be true?"),
        verificationHint: z.string().trim(),
      }),
    )
    .min(1, "a story with no acceptance criteria verifies nothing"),
});

type FormValues = z.infer<typeof schema>;

const EMPTY_CRITERION = { criterionId: "", description: "", verificationHint: "" };

export function StoriesPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const gateways = useGateways();
  const queryClient = useQueryClient();

  const stories = useQuery({
    queryKey: ["stories", projectId],
    queryFn: () => gateways.stories.list(projectId),
  });

  // Compiling needs the policy the plan will run under. Read from the project rather
  // than asked for: the resolution order is the server's (docs/12), and a second place
  // to choose one is a second place for the two to disagree.
  const { project } = useProjectViewModel(projectId);
  const runPolicyId = project?.defaultRunPolicyId ?? null;

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { actor: "", goal: "", criteria: [EMPTY_CRITERION] },
  });

  const criteria = useFieldArray({ control, name: "criteria" });
  // `useWatch` rather than `watch()`: the latter returns a fresh function on every
  // render, which React's compiler cannot memoize safely.
  const draftCriteria = useWatch({ control, name: "criteria" });
  const withoutHint = draftCriteria.filter(
    (criterion) => criterion.verificationHint.trim() === "",
  ).length;

  const create = useMutation({
    mutationFn: (values: FormValues) =>
      gateways.stories.create({
        projectId,
        actor: values.actor,
        goal: values.goal,
        acceptanceCriteria: values.criteria.map((criterion) => ({
          criterionId: criterion.criterionId,
          description: criterion.description,
          verificationHint: criterion.verificationHint === "" ? null : criterion.verificationHint,
        })),
      }),
    onSuccess: () => {
      reset({ actor: "", goal: "", criteria: [EMPTY_CRITERION] });
      void queryClient.invalidateQueries({ queryKey: ["stories", projectId] });
    },
  });

  const compile = useMutation({
    mutationFn: (storyId: string) => {
      if (runPolicyId === null) {
        // Refused here with the reason, rather than sent and bounced as a validation
        // error the reader would have to decode.
        throw new Error(
          "this project has no default run policy, so a plan has no limits to run under",
        );
      }
      return gateways.stories.compile(storyId, runPolicyId);
    },
    onSuccess: () => {
      void navigate(`/projects/${projectId}/runs/new`);
    },
  });

  return (
    <section>
      <PageTitle>Stories</PageTitle>
      <Lede>
        What this application is supposed to do, in the words a report will quote back.
      </Lede>

      <ul className="mb-8 grid gap-4">
        {(stories.data ?? []).map((story) => {
          const unchecked = unverifiable(story);
          return (
            <li
              className="min-w-0 rounded-lg bg-white p-4 shadow-xs dark:bg-gray-800"
              key={story.storyId}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-gray-700 dark:text-gray-200">
                    As {story.actor}, {story.goal}
                  </p>
                  <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    {story.acceptanceCriteria.length} criteria
                    {unchecked.length > 0 ? (
                      <>
                        {" · "}
                        <span className="text-yellow-600 dark:text-yellow-400">
                          {unchecked.length} judged by a model
                        </span>
                      </>
                    ) : null}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => compile.mutate(story.storyId)}
                  disabled={compile.isPending || runPolicyId === null}
                >
                  {compile.isPending ? "Compiling…" : "Compile into a plan"}
                </Button>
              </div>

              {isFullyModelJudged(story) ? (
                <div className="mt-3">
                  <Notice tone="warning">
                    No criterion here can be checked deterministically, so a run of this
                    story can only end <code>inconclusive</code> — never a pass or a defect.
                  </Notice>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {stories.data?.length === 0 ? <Notice>No stories yet.</Notice> : null}

      {runPolicyId === null && (stories.data?.length ?? 0) > 0 ? (
        <Notice tone="warning">
          This project has no default run policy, so a story cannot be compiled into a plan
          yet — a plan with no limits is one nobody chose.
        </Notice>
      ) : null}

      {compile.error !== null ? (
        <Notice tone="error">
          {compile.error instanceof Error ? compile.error.message : "the plan was not compiled"}
        </Notice>
      ) : null}

      <Card>
        <SectionTitle>New story</SectionTitle>
        <form onSubmit={(event) => void handleSubmit((values) => create.mutate(values))(event)}>
          <Field label="As" htmlFor="actor" error={errors.actor?.message}>
            <input
              id="actor"
              className={inputClass(errors.actor !== undefined)}
              {...register("actor")}
              placeholder="a signed-in customer"
            />
          </Field>

          <Field label="I want to" htmlFor="goal" error={errors.goal?.message}>
            <input
              id="goal"
              className={inputClass(errors.goal !== undefined)}
              {...register("goal")}
              placeholder="place an order"
            />
          </Field>

          <h4 className="mt-6 mb-2 text-sm font-semibold text-gray-600 dark:text-gray-300">
            Acceptance criteria
          </h4>
          {criteria.fields.map((field, index) => (
            <fieldset
              className="mb-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700"
              key={field.id}
            >
              <Field
                label="Id"
                htmlFor={`criterion-${index}`}
                error={errors.criteria?.[index]?.criterionId?.message}
              >
                <input
                  id={`criterion-${index}`}
                  className={inputClass(errors.criteria?.[index]?.criterionId !== undefined)}
                  {...register(`criteria.${index}.criterionId`)}
                  placeholder="ac-order-confirmed"
                />
              </Field>

              <Field
                label="Has to be true"
                htmlFor={`description-${index}`}
                error={errors.criteria?.[index]?.description?.message}
              >
                <input
                  id={`description-${index}`}
                  className={inputClass(errors.criteria?.[index]?.description !== undefined)}
                  {...register(`criteria.${index}.description`)}
                  placeholder="the order confirmation page appears"
                />
              </Field>

              <Field
                label="Text the page must contain"
                htmlFor={`hint-${index}`}
                hint="Leave it empty and a model judges this criterion — which can never fail the product, only leave the run inconclusive."
              >
                <input
                  id={`hint-${index}`}
                  className={inputClass()}
                  {...register(`criteria.${index}.verificationHint`)}
                  placeholder="Order confirmed"
                />
              </Field>

              {criteria.fields.length > 1 ? (
                <div className="mt-4">
                  <Button variant="secondary" type="button" onClick={() => criteria.remove(index)}>
                    Remove criterion
                  </Button>
                </div>
              ) : null}
            </fieldset>
          ))}

          {errors.criteria?.root ? (
            <p className="text-xs text-red-600 dark:text-red-400">{errors.criteria.root.message}</p>
          ) : null}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button variant="secondary" type="button" onClick={() => criteria.append(EMPTY_CRITERION)}>
              Add criterion
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Save story"}
            </Button>
          </div>

          {withoutHint > 0 ? (
            <div className="mt-4">
              <Notice tone="warning">
                {withoutHint} of {draftCriteria.length} criteria have no text to check for. A
                run can only report <code>inconclusive</code> for those.
              </Notice>
            </div>
          ) : null}

          {create.error !== null ? (
            <div className="mt-4">
              <Notice tone="error">
                {create.error instanceof Error ? create.error.message : "the story was not saved"}
              </Notice>
            </div>
          ) : null}
        </form>
      </Card>
    </section>
  );
}
