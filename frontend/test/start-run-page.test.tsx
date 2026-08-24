/**
 * The one run nobody can answer.
 *
 * ADR 0017 says a run may carry a story, a sweep, or both. The fourth combination —
 * neither — is the one it does not describe, and it has exactly one possible outcome.
 * Measured against a real site: the server accepts it with 201, the worker launches
 * Chromium, and ten seconds later the report is `inconclusive` with zero criteria and no
 * stated reason.
 *
 * The API stays permissive on purpose — a bare run is how the durability tests exercise
 * the lifecycle — so this screen is where it stops being offered.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Gateways } from "@viewmodels/gateways";
import type { Project } from "@domain/projects/project";

import App from "../src/App";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeSessionGateway,
  FakeStoryGateway,
} from "./fakes";

const PROJECT: Project = {
  projectId: "proj-1",
  name: "Checkout",
  defaultRunPolicyId: "pol-1",
};

function renderStartRun() {
  const runs = new FakeRunGateway();
  const gateways: Gateways = {
    projects: new FakeProjectGateway([PROJECT]),
    runs,
    events: new FakeRunEventStream(),
    memory: new FakeMemoryGateway(),
    stories: new FakeStoryGateway(),
    sessions: new FakeSessionGateway(),
  };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <MemoryRouter initialEntries={["/projects/proj-1/runs/new"]}>
      <App gateways={gateways} queryClient={queryClient} />
    </MemoryRouter>,
  );
  return runs;
}

describe("starting a run", () => {
  it("does not offer a run that has nothing to check", async () => {
    renderStartRun();

    const start = await screen.findByRole("button", { name: "Start run" });

    expect(start).toBeDisabled();
    // Disabled with no explanation is its own dead end, so the reason is on screen.
    expect(screen.getByText(/has nothing to check/)).toBeInTheDocument();
  });

  it("offers it once the run is asked to walk the site", async () => {
    const runs = renderStartRun();

    await userEvent.click(screen.getByLabelText("Walk the site as well"));
    await userEvent.click(screen.getByRole("button", { name: "Start run" }));

    expect(runs.started).toHaveLength(1);
    expect(runs.started[0]?.explore).toBe(true);
  });

  it("offers it once a plan is named, with no crawl", async () => {
    const runs = renderStartRun();

    await userEvent.type(screen.getByLabelText("Plan id"), "plan-7");
    await userEvent.click(screen.getByRole("button", { name: "Start run" }));

    expect(runs.started).toHaveLength(1);
    expect(runs.started[0]?.planId).toBe("plan-7");
    expect(runs.started[0]?.explore).toBeUndefined();
  });

  it("treats whitespace as an empty plan id", async () => {
    // Otherwise a stray space buys back the exact run this screen refuses to offer.
    renderStartRun();

    await userEvent.type(screen.getByLabelText("Plan id"), "   ");

    expect(await screen.findByRole("button", { name: "Start run" })).toBeDisabled();
  });
});
