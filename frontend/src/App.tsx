import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router";

import { GatewaysProvider } from "@viewmodels/gateways-context";
import { AppShell } from "@views/components/app-shell";
import type { Gateways } from "@viewmodels/gateways";
import { Notice } from "@views/components/ui";
import { MemoryPage } from "@views/pages/memory-page";
import { ProjectPage } from "@views/pages/project-page";
import { ProjectsPage } from "@views/pages/projects-page";
import { RunPage } from "@views/pages/run-page";
import { StartRunPage } from "@views/pages/start-run-page";
import { StoriesPage } from "@views/pages/stories-page";

import "@views/styles/theme.css";

/**
 * The app shell.
 *
 * Both providers are injectable so a test renders the real routes against fake
 * gateways — the routing and the screens are what a test should exercise, and a real
 * `fetch` in one would only make it slower and flakier.
 */
export function App({
  gateways,
  queryClient,
}: {
  gateways?: Gateways;
  queryClient?: QueryClient;
}) {
  const client = queryClient ?? defaultQueryClient();

  return (
    <QueryClientProvider client={client}>
      <GatewaysProvider {...(gateways === undefined ? {} : { gateways })}>
        <AppShell>
          <Routes>
            <Route path="/" element={<Navigate to="/projects" replace />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/projects/:projectId/runs/new" element={<StartRunPage />} />
            <Route path="/projects/:projectId/memory" element={<MemoryPage />} />
            <Route path="/projects/:projectId/stories" element={<StoriesPage />} />
            <Route path="/runs/:runId" element={<RunPage />} />
            <Route path="*" element={<Notice>No such page.</Notice>} />
          </Routes>
        </AppShell>
      </GatewaysProvider>
    </QueryClientProvider>
  );
}

function defaultQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // A control plane's data is worth refetching when someone comes back to the
        // tab: a stale project list is how a run gets started against the wrong thing.
        staleTime: 5_000,
        retry: 1,
      },
    },
  });
}

export default App;
