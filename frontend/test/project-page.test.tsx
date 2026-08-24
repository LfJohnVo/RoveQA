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
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Gateways } from "@viewmodels/gateways";
import type { Project } from "@domain/projects/project";
import type { EnvironmentSession } from "@domain/projects/session";
import type { Run } from "@domain/runs/run";

import App from "../src/App";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeSessionGateway,
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
    sessions: new FakeSessionGateway(),
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

describe("a project's sessions", () => {
  function withEnvironment(sessions: EnvironmentSession[]): FakeSessionGateway {
    const gateway = new FakeSessionGateway();
    gateway.known = [
      { environmentId: "env-1", projectId: "proj-1", name: "staging", defaultRunPolicyId: null },
    ];
    gateway.registered = sessions;
    return gateway;
  }

  function renderWith(gateway: FakeSessionGateway) {
    const gateways: Gateways = {
      projects: new FakeProjectGateway([PROJECT]),
      runs: new FakeRunGateway(),
      events: new FakeRunEventStream(),
      memory: new FakeMemoryGateway(),
      stories: new FakeStoryGateway(),
      sessions: gateway,
    };
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter initialEntries={["/projects/proj-1"]}>
        <App gateways={gateways} queryClient={queryClient} />
      </MemoryRouter>,
    );
  }

  function session(overrides: Partial<EnvironmentSession> = {}): EnvironmentSession {
    return {
      sessionId: "sess-1",
      environmentId: "env-1",
      label: "admin",
      establishedAt: "2026-08-23T10:00:00Z",
      validUntil: null,
      establishedBy: "captured by hand",
      ...overrides,
    };
  }

  it("says an environment with no session goes out anonymous", async () => {
    renderWith(withEnvironment([]));

    expect(await screen.findByText("anonymous")).toBeInTheDocument();
  });

  it("names the session a run would borrow", async () => {
    renderWith(withEnvironment([session()]));

    expect(await screen.findByText("admin")).toBeInTheDocument();
  });

  it("never renders anything a session contains", async () => {
    // There is no field on the domain type to hold one, so this asserts the shape stays
    // that way: a screen that could show a cookie is one screenshot from leaking it.
    renderWith(withEnvironment([session()]));
    await screen.findByText("admin");

    expect(document.body.textContent).not.toContain("storage_state");
    expect(document.body.textContent).not.toContain("cookie");
  });

  it("distinguishes no stated expiry from an expiry that passed", async () => {
    // Colouring "nobody said" as "it is over" would train people to ignore the colour.
    renderWith(withEnvironment([session()]));

    expect(await screen.findByText("no stated expiry")).toBeInTheDocument();
  });

  it("marks a session whose stated validity is over", async () => {
    renderWith(withEnvironment([session({ validUntil: "2020-01-01T00:00:00Z" })]));

    expect(await screen.findByText("expired")).toBeInTheDocument();
  });

  it("revokes the session a run would borrow", async () => {
    const gateway = withEnvironment([session()]);
    renderWith(gateway);
    await screen.findByText("admin");

    await userEvent.click(screen.getByRole("button", { name: "Revoke" }));

    expect(gateway.revoked).toEqual(["sess-1"]);
  });

  it("offers no way to register one from the browser", async () => {
    // Deliberate: `roveqa session register <file>` reads a credential once and sends it
    // once, while a paste box routes it through browser memory and autofill for nothing.
    renderWith(withEnvironment([]));
    await screen.findByText("anonymous");

    expect(screen.queryByRole("button", { name: /register/i })).toBeNull();
    expect(screen.queryByLabelText(/storage state/i)).toBeNull();
  });
});
