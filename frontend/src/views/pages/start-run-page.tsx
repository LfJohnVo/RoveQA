import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router";
import { z } from "zod";

import { prepareRun } from "@application/usecases/start-run";
import { useGateways } from "@viewmodels/gateways-context";
import { Button, Card, Field, Lede, Notice, PageTitle } from "@views/components/ui";
import { inputClass } from "@views/components/form-classes";

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
});

type FormValues = z.infer<typeof schema>;

export function StartRunPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const gateways = useGateways();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

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
        Leave the plan empty for an exploratory run. A run with no plan verifies nothing, so
        it reports{" "}
        <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs dark:bg-gray-700">
          inconclusive
        </code>{" "}
        rather than a pass.
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
            <Button type="submit" disabled={start.isPending}>
              {start.isPending ? "Starting…" : "Start run"}
            </Button>
          </div>
        </form>
      </Card>
    </section>
  );
}
