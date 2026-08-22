/**
 * The way back to a run.
 *
 * A report the console cannot reach is a report nobody reads. Until this screen listed
 * a project's runs, a run was only reachable while the tab that started it stayed open:
 * everything launched by a schedule, by the CLI, or yesterday had a finished report in
 * the database and no route to it.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Gateways } from "@viewmodels/gateways";
import type { Project } from "@domain/projects/project";
import type { Run } from "@domain/runs/run";

import App from "../src/App";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeStoryGateway,
  makeRun,
} from "./fakes";

const PROJECT: Project = {
  projectId: "proj-1",
  name: "Checkout",
  defaultRunPolicyId: "pol-1",
};

function renderProject(history: Run[]) {
  const runs = new FakeRunGateway();
  runs.history = history;
  const gateways: Gateways = {
    projects: new FakeProjectGateway([PROJECT]),
    runs,
    events: new FakeRunEventStream(),
    memory: new FakeMemoryGateway(),
    stories: new FakeStoryGateway(),
  };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <MemoryRouter initialEntries={["/projects/proj-1"]}>
      <App gateways={gateways} queryClient={queryClient} />
    </MemoryRouter>,
  );
  return runs;
}

describe("a project's runs", () => {
  it("links to a run this session did not start", async () => {
    renderProject([
      makeRun({ runId: "run-earlier", status: "completed", verdict: "passed" }),
    ]);

    const link = await screen.findByRole("link", { name: "run-earlier" });
    expect(link).toHaveAttribute("href", "/runs/run-earlier");
  });

  it("shows the verdict of a finished run and no verdict for one still going", async () => {
    renderProject([
      makeRun({ runId: "run-done", status: "completed", verdict: "blocked" }),
      makeRun({ runId: "run-going", status: "running", verdict: null }),
    ]);

    const done = (await screen.findByText("run-done")).closest("tr");
    const going = screen.getByText("run-going").closest("tr");

    expect(done).not.toBeNull();
    expect(going).not.toBeNull();
    expect(within(done as HTMLElement).getByText("blocked")).toBeInTheDocument();
    // A run still going has concluded nothing. A badge here would report the absence of
    // an answer as if it were one.
    expect(within(going as HTMLElement).queryByText("inconclusive")).toBeNull();
  });

  it("says a run explored rather than leaving the plan blank", async () => {
    renderProject([makeRun({ runId: "run-crawl", planId: null, planVersion: null })]);

    const row = (await screen.findByText("run-crawl")).closest("tr");
    expect(within(row as HTMLElement).getByText("exploration")).toBeInTheDocument();
  });

  it("says so when a project has never run, instead of showing an empty table", async () => {
    renderProject([]);

    expect(await screen.findByText(/No runs yet/)).toBeInTheDocument();
  });

  it("asks only for this project's runs", async () => {
    const runs = renderProject([
      makeRun({ runId: "mine", projectId: "proj-1" }),
      makeRun({ runId: "somebody-elses", projectId: "proj-2" }),
    ]);

    await screen.findByText("mine");
    expect(screen.queryByText("somebody-elses")).toBeNull();
    expect(runs.history).toHaveLength(2); // the filter is the gateway's, not the view's
  });
});
