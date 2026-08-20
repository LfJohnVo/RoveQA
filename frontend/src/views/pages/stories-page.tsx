import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { useNavigate, useParams } from "react-router";
import { z } from "zod";

import { isFullyModelJudged, unverifiable } from "@domain/qa/story";
import { useGateways } from "@viewmodels/gateways-context";
import { useProjectViewModel } from "@viewmodels/projects/use-projects-viewmodel";

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
      <h2 className="page__title">Stories</h2>
      <p className="page__lede">
        What this application is supposed to do, in the words a report will quote back.
      </p>

      <ul className="card-list">
        {(stories.data ?? []).map((story) => {
          const unchecked = unverifiable(story);
          return (
            <li className="card" key={story.storyId}>
              <div className="card__name">
                As {story.actor}, {story.goal}
              </div>
              <div className="card__meta">
                {story.acceptanceCriteria.length} criteria
                {unchecked.length > 0 ? ` · ${unchecked.length} judged by a model` : ""}
              </div>
              {isFullyModelJudged(story) ? (
                <p className="notice" role="status">
                  No criterion here can be checked deterministically, so a run of this
                  story can only end <code>inconclusive</code> — never a pass or a
                  defect.
                </p>
              ) : null}
              <button
                className="button"
                type="button"
                onClick={() => compile.mutate(story.storyId)}
                disabled={compile.isPending || runPolicyId === null}
              >
                {compile.isPending ? "Compiling…" : "Compile into a plan"}
              </button>
            </li>
          );
        })}
      </ul>

      {stories.data?.length === 0 ? <p className="notice">No stories yet.</p> : null}

      {runPolicyId === null && (stories.data?.length ?? 0) > 0 ? (
        <p className="notice" role="status">
          This project has no default run policy, so a story cannot be compiled into a
          plan yet — a plan with no limits is one nobody chose.
        </p>
      ) : null}

      {compile.error !== null ? (
        <p className="notice notice--error" role="alert">
          {compile.error instanceof Error ? compile.error.message : "the plan was not compiled"}
        </p>
      ) : null}

      <h3 className="section__title">New story</h3>
      <form onSubmit={(event) => void handleSubmit((values) => create.mutate(values))(event)}>
        <div className="field">
          <label htmlFor="actor">As</label>
          <input id="actor" {...register("actor")} placeholder="a signed-in customer" />
          {errors.actor ? <span className="field__error">{errors.actor.message}</span> : null}
        </div>

        <div className="field">
          <label htmlFor="goal">I want to</label>
          <input id="goal" {...register("goal")} placeholder="place an order" />
          {errors.goal ? <span className="field__error">{errors.goal.message}</span> : null}
        </div>

        <h4 className="section__title">Acceptance criteria</h4>
        {criteria.fields.map((field, index) => (
          <fieldset className="criterion" key={field.id}>
            <div className="field">
              <label htmlFor={`criterion-${index}`}>Id</label>
              <input
                id={`criterion-${index}`}
                {...register(`criteria.${index}.criterionId`)}
                placeholder="ac-order-confirmed"
              />
              {errors.criteria?.[index]?.criterionId ? (
                <span className="field__error">
                  {errors.criteria[index].criterionId.message}
                </span>
              ) : null}
            </div>

            <div className="field">
              <label htmlFor={`description-${index}`}>Has to be true</label>
              <input
                id={`description-${index}`}
                {...register(`criteria.${index}.description`)}
                placeholder="the order confirmation page appears"
              />
              {errors.criteria?.[index]?.description ? (
                <span className="field__error">
                  {errors.criteria[index].description.message}
                </span>
              ) : null}
            </div>

            <div className="field">
              <label htmlFor={`hint-${index}`}>Text the page must contain</label>
              <input
                id={`hint-${index}`}
                {...register(`criteria.${index}.verificationHint`)}
                placeholder="Order confirmed"
              />
              <span className="field__note">
                Leave it empty and a model judges this criterion — which can never fail
                the product, only leave the run inconclusive.
              </span>
            </div>

            {criteria.fields.length > 1 ? (
              <button className="button" type="button" onClick={() => criteria.remove(index)}>
                Remove criterion
              </button>
            ) : null}
          </fieldset>
        ))}

        {errors.criteria?.root ? (
          <p className="field__error">{errors.criteria.root.message}</p>
        ) : null}

        <div className="commands">
          <button
            className="button"
            type="button"
            onClick={() => criteria.append(EMPTY_CRITERION)}
          >
            Add criterion
          </button>
          <button className="button button--primary" type="submit" disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save story"}
          </button>
        </div>

        {withoutHint > 0 ? (
          <p className="notice" role="status">
            {withoutHint} of {draftCriteria.length} criteria have no text to check for. A
            run can only report <code>inconclusive</code> for those.
          </p>
        ) : null}

        {create.error !== null ? (
          <p className="notice notice--error" role="alert">
            {create.error instanceof Error ? create.error.message : "the story was not saved"}
          </p>
        ) : null}
      </form>
    </section>
  );
}
