/**
 * The project list and one project's detail.
 *
 * Server state through TanStack Query (docs/04): it owns caching, staleness and
 * refetching, and reimplementing that in a `useEffect` is how a list ends up showing
 * a project that was deleted two screens ago.
 */

import { useQuery } from "@tanstack/react-query";

import type { Project } from "@domain/projects/project";
import { useGateways } from "@viewmodels/gateways-context";

const DEFAULT_LIMIT = 50;

export interface ProjectsViewModel {
  projects: readonly Project[];
  isLoading: boolean;
  error: string | null;
}

export function useProjectsViewModel(limit = DEFAULT_LIMIT): ProjectsViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["projects", limit],
    queryFn: () => gateways.projects.list(limit),
  });

  return {
    projects: query.data ?? [],
    isLoading: query.isPending,
    error: query.error === null ? null : messageFor(query.error),
  };
}

export interface ProjectViewModel {
  project: Project | null;
  isLoading: boolean;
  /** Distinguished from a generic error: a project that does not exist is a wrong URL,
   * not a broken control plane, and the two deserve different screens. */
  notFound: boolean;
  error: string | null;
}

export function useProjectViewModel(projectId: string): ProjectViewModel {
  const gateways = useGateways();
  const query = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => gateways.projects.get(projectId),
    retry: (failureCount, error) => !isNotFound(error) && failureCount < 2,
  });

  const notFound = query.error !== null && isNotFound(query.error);
  return {
    project: query.data ?? null,
    isLoading: query.isPending,
    notFound,
    error: query.error === null || notFound ? null : messageFor(query.error),
  };
}

function isNotFound(error: unknown): boolean {
  return typeof error === "object" && error !== null && "status" in error
    ? (error as { status: unknown }).status === 404
    : false;
}

function messageFor(cause: unknown): string {
  return cause instanceof Error ? cause.message : "the control plane did not answer";
}
