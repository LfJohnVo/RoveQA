/**
 * Which environments a project has, and what session each one would lend a run.
 *
 * Read and revoke. There is no register here, and that is a decision rather than an
 * omission: pasting a credential into a web form routes it through browser memory,
 * autofill and anything that screenshots the tab, for no gain over
 * `roveqa session register <file>`, which reads it once and sends it once (ADR 0019).
 *
 * What the console is for is the operational question — is this environment
 * authenticated, is its session about to expire, take it away now — and none of that
 * needs the session itself.
 */

import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";

import type { Environment, EnvironmentSession } from "@domain/projects/session";
import { currentSession, hasExpired } from "@domain/projects/session";
import { useGateways } from "@viewmodels/gateways-context";

export interface EnvironmentSessions {
  environment: Environment;
  sessions: readonly EnvironmentSession[];
  /** The one a run would borrow, or null when the environment has none. */
  current: EnvironmentSession | null;
  /** True only when an expiry was stated and has passed. Unknown validity is not
   *  expiry, and colouring it as one would train people to ignore the colour. */
  expired: boolean;
}

export interface SessionsViewModel {
  environments: readonly EnvironmentSessions[];
  isLoading: boolean;
  error: string | null;
  revoke: (environmentId: string, sessionId: string) => void;
  isRevoking: boolean;
  revokeError: string | null;
}

export function useSessionsViewModel(projectId: string, now = new Date()): SessionsViewModel {
  const gateways = useGateways();
  const queryClient = useQueryClient();

  // One query for the environments, then one per environment for its sessions. Written
  // with `useQueries` rather than a loop of hooks because the count is data: a project
  // can have one environment today and three tomorrow, and hooks cannot be conditional.
  const [environmentsQuery] = useQueries({
    queries: [
      {
        queryKey: ["environments", projectId],
        queryFn: () => gateways.sessions.environments(projectId),
      },
    ],
  });
  const environments = environmentsQuery?.data ?? [];

  const sessionQueries = useQueries({
    queries: environments.map((environment) => ({
      queryKey: ["sessions", environment.environmentId],
      queryFn: () => gateways.sessions.sessions(environment.environmentId),
    })),
  });

  const mutation = useMutation({
    mutationFn: ({ environmentId, sessionId }: { environmentId: string; sessionId: string }) =>
      gateways.sessions.revoke(environmentId, sessionId),
    onSuccess: async (_result, variables) => {
      // Refetched rather than spliced, because the row does *not* disappear: revoking
      // destroys a key and leaves the record. A cache edit here would have to guess at
      // that, and guessing the other way would show the session as gone when it is not.
      await queryClient.invalidateQueries({ queryKey: ["sessions", variables.environmentId] });
    },
  });

  const rows: EnvironmentSessions[] = environments.map((environment, index) => {
    const sessions = sessionQueries[index]?.data ?? [];
    const current = currentSession(sessions);
    return {
      environment,
      sessions,
      current,
      expired: current !== null && hasExpired(current, now),
    };
  });

  return {
    environments: rows,
    isLoading: environmentsQuery?.isPending ?? false,
    error: messageOr(environmentsQuery?.error, null),
    revoke: (environmentId, sessionId) => mutation.mutate({ environmentId, sessionId }),
    isRevoking: mutation.isPending,
    revokeError: messageOr(mutation.error, null),
  };
}

function messageOr(cause: unknown, fallback: string | null): string | null {
  if (cause === null || cause === undefined) return fallback;
  return cause instanceof Error ? cause.message : "the control plane did not answer";
}
