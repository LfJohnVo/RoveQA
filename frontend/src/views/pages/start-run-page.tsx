import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router";
import { z } from "zod";

import { prepareRun } from "@application/usecases/start-run";
import { useGateways } from "@viewmodels/gateways-context";

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
      <h2 className="page__title">Start a run</h2>
      <p className="page__lede">
        Leave the plan empty for an exploratory run. A run with no plan verifies nothing,
        so it reports <code>inconclusive</code> rather than a pass.
      </p>

      <form onSubmit={(event) => void handleSubmit((values) => start.mutate(values))(event)}>
        <div className="field">
          <label htmlFor="planId">Plan id</label>
          <input id="planId" {...register("planId")} placeholder="optional" />
          {errors.planId ? <span className="field__error">{errors.planId.message}</span> : null}
        </div>

        <div className="field">
          <label htmlFor="planVersion">Plan version</label>
          <input id="planVersion" {...register("planVersion")} placeholder="optional" />
        </div>

        <div className="field">
          <label htmlFor="environmentId">Environment</label>
          <input id="environmentId" {...register("environmentId")} placeholder="optional" />
        </div>

        {start.error !== null ? (
          <p className="notice notice--error" role="alert">
            {start.error instanceof Error ? start.error.message : "the run could not be started"}
          </p>
        ) : null}

        <button className="button button--primary" type="submit" disabled={start.isPending}>
          {start.isPending ? "Starting…" : "Start run"}
        </button>
      </form>
    </section>
  );
}
