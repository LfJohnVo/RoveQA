/**
 * The knowledge browser.
 *
 * What it has to get right is a distinction, not a layout: durable knowledge and the
 * graph projection are separate, and a graph that is down or behind is a slower next
 * run rather than lost memory. A screen that blurred those two would send someone
 * chasing a data-loss incident that did not happen.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import App from "../src/App";
import type { Gateways } from "@viewmodels/gateways";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeStoryGateway,
  makeMemoryStatus,
} from "./fakes";

function renderMemory(memory: FakeMemoryGateway) {
  const gateways: Gateways = {
    projects: new FakeProjectGateway(),
    runs: new FakeRunGateway(),
    events: new FakeRunEventStream(),
    memory,
    stories: new FakeStoryGateway(),
  };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <MemoryRouter initialEntries={["/projects/proj-1/memory"]}>
      <App gateways={gateways} queryClient={queryClient} />
    </MemoryRouter>,
  );
}

describe("durable knowledge and the projection are shown apart", () => {
  it("reports both counts", async () => {
    renderMemory(
      new FakeMemoryGateway(
        makeMemoryStatus({
          durableCandidates: 12,
          actionableCandidates: 5,
          byStatus: { candidate: 7, promoted: 4, trusted: 1 },
        }),
      ),
    );

    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("says nothing was lost when the graph is unreachable", async () => {
    renderMemory(
      new FakeMemoryGateway(makeMemoryStatus({ graphAvailable: false, durableCandidates: 12 })),
    );

    expect(await screen.findByText(/Nothing has been lost/)).toBeInTheDocument();
    expect(screen.getByText("unavailable")).toBeInTheDocument();
  });

  it("explains a backlog as work kept rather than work failed", async () => {
    renderMemory(new FakeMemoryGateway(makeMemoryStatus({ syncPending: 9, syncFailed: 1 })));

    expect(await screen.findByText(/backlog kept the work/)).toBeInTheDocument();
  });
});

describe("an empty project", () => {
  it("explains why there is nothing rather than looking broken", async () => {
    // "No data" and "one run is not enough yet" look identical unless the screen says
    // which one it is.
    renderMemory(new FakeMemoryGateway(makeMemoryStatus()));

    expect(await screen.findByText(/two independent runs agree/)).toBeInTheDocument();
  });
});
