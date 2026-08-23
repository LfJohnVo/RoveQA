import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";
import { useNavigate, useParams } from "react-router";
import { z } from "zod";

import { prepareRun } from "@application/usecases/start-run";
import { useGateways } from "@viewmodels/gateways-context";
import { Button, Card, Field, Lede, Notice, PageTitle } from "@views/components/ui";
import { checkboxClass, inputClass } from "@views/components/form-classes";

/**
 * Starting a run.
 *
 * One schema, used by the resolver and nowhere else — validation rules duplicated in a
 * component drift from the ones that actually run (`.claude/rules/frontend.md`).
 *
 * The idempotency key is minted once per submission by `prepareRun` and reused if the
 * request is retried. A user who double-submits, or a network that loses the response,
 * must not end up with two runs against their application (docs/12).
 */
const schema = z.object({
  planId: z.string().trim().optional(),
  planVersion: z.string().trim().optional(),
  environmentId: z.string().trim().optional(),
  explore: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function StartRunPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const gateways = useGateways();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    // Off unless asked. A default of `true` would make every run a crawl, which is
    // a different question from the one most people came to ask.
    defaultValues: { explore: false },
  });

  // A run with neither a plan nor a crawl is the one combination ADR 0017 does not
  // describe, and it is answerable only one way. Measured: the server accepts it with
  // 201, the worker launches Chromium, and ten seconds later the report is
  // `inconclusive` with zero criteria and no stated reason — a run that could never have
  // concluded anything. The API stays permissive on purpose (a bare run is how the
  // durability tests exercise the lifecycle), so the place to stop offering it is here.
  // `useWatch` rather than `watch`: the latter returns a function the React Compiler
  // cannot memoize safely, so it skips optimising the whole component. This subscribes
  // to the two fields the button depends on and nothing else.
  //
  // `?? ""` matters. An untouched field arrives as `undefined`, not as the empty string,
  // so comparing against `""` alone would miss the one state this exists for — a form
  // nobody has typed in.
  const [planId, explore] = useWatch({ control, name: ["planId", "explore"] });
  const asksForNothing = (planId ?? "").trim() === "" && explore !== true;

  const start = useMutation({
    mutationFn: (values: FormValues) => {
      const attempt = prepareRun(gateways.runs, {
        projectId,
        ...(values.planId !== undefined && values.planId !== "" ? { planId: values.planId } : {}),
        ...(values.planVersion !== undefined && values.planVersion !== ""
          ? { planVersion: values.planVersion }
          : {}),
        ...(values.environmentId !== undefined && values.environmentId !== ""
          ? { environmentId: values.environmentId }
          : {}),
        ...(values.explore === true ? { explore: true } : {}),
      });
      return attempt.run();
    },
    onSuccess: (run) => {
      void navigate(`/runs/${run.runId}`);
    },
  });

  return (
    <section>
      <PageTitle>Start a run</PageTitle>
      <Lede>
        A run can follow a story, walk the site, or do both. Every run checks each page it
        reaches — that it answered, and what it answered — so a traversal with no story
        still comes back with a verdict rather than a shrug.
      </Lede>

      <Card className="mb-8">
        <form onSubmit={(event) => void handleSubmit((values) => start.mutate(values))(event)}>
          <Field label="Plan id" htmlFor="planId" error={errors.planId?.message}>
            <input
              id="planId"
              className={inputClass(errors.planId !== undefined)}
              {...register("planId")}
              placeholder="optional"
            />
          </Field>

          <Field label="Plan version" htmlFor="planVersion">
            <input
              id="planVersion"
              className={inputClass()}
              {...register("planVersion")}
              placeholder="optional"
            />
          </Field>

          <div className="mt-4">
            <label className="flex items-center text-sm text-gray-700 dark:text-gray-400">
              <input id="explore" type="checkbox" className={checkboxClass()} {...register("explore")} />
              <span className="ml-2">Walk the site as well</span>
            </label>
            <span className="mt-1 block text-xs text-gray-600 dark:text-gray-400">
              Follows the links each page offers, deciding from the page rather than from a
              model — so a traversal costs no inference at all. Combine it with a plan and
              the story's criteria are credited wherever the crawl meets them.
            </span>
          </div>

          <Field label="Environment" htmlFor="environmentId">
            <input
              id="environmentId"
              className={inputClass()}
              {...register("environmentId")}
              placeholder="optional"
            />
          </Field>

          {start.error !== null ? (
            <div className="mt-4">
              <Notice tone="error">
                {start.error instanceof Error
                  ? start.error.message
                  : "the run could not be started"}
              </Notice>
            </div>
          ) : null}

          <div className="mt-6">
            <Button type="submit" disabled={start.isPending || asksForNothing}>
              {start.isPending ? "Starting…" : "Start run"}
            </Button>
            {asksForNothing ? (
              <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                Name a plan, tick “Walk the site as well”, or both. A run asked for neither
                has nothing to check and comes back inconclusive.
              </p>
            ) : null}
          </div>
        </form>
      </Card>
    </section>
  );
}
