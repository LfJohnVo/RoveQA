/**
 * The way in.
 *
 * Until this form existed the only way to create a project was `curl`, which made the
 * whole interface a viewer of work started somewhere else. What it has to get right is
 * that a project arrives *able to run*: the origin and the budgets are part of creating
 * it, because a project without a run policy cannot compile a plan or start anything.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Gateways } from "@viewmodels/gateways";

import App from "../src/App";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeStoryGateway,
} from "./fakes";

function renderProjects(projects: FakeProjectGateway) {
  const gateways: Gateways = {
    projects,
    runs: new FakeRunGateway(),
    events: new FakeRunEventStream(),
    memory: new FakeMemoryGateway(),
    stories: new FakeStoryGateway(),
  };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <MemoryRouter initialEntries={["/projects"]}>
      <App gateways={gateways} queryClient={queryClient} />
    </MemoryRouter>,
  );
}

async function openForm() {
  await userEvent.click(screen.getByRole("button", { name: "New project" }));
}

describe("creating the first project", () => {
  it("sends the origin and the budgets with it", async () => {
    const projects = new FakeProjectGateway();
    renderProjects(projects);
    await openForm();

    await userEvent.type(screen.getByLabelText("Name"), "Checkout");
    await userEvent.type(screen.getByLabelText("Application origin"), "http://localhost:3000");
    await userEvent.click(screen.getByRole("button", { name: "Create project" }));

    await screen.findByText("Checkout");
    expect(projects.created).toHaveLength(1);
    expect(projects.created[0]).toMatchObject({
      name: "Checkout",
      allowedOrigins: ["http://localhost:3000"],
      // Off unless asked for, here as on the server: a policy that permits writes is a
      // decision somebody makes, never one they inherit from a form default.
      destructiveActions: false,
    });
  });

  it("refuses an origin with a path, before anything is created", async () => {
    const projects = new FakeProjectGateway();
    renderProjects(projects);
    await openForm();

    await userEvent.type(screen.getByLabelText("Name"), "Checkout");
    await userEvent.type(
      screen.getByLabelText("Application origin"),
      "http://localhost:3000/checkout",
    );
    await userEvent.click(screen.getByRole("button", { name: "Create project" }));

    // The server would refuse it too. Saying so here costs nothing and does not leave a
    // half-made project behind.
    expect(await screen.findByText(/scheme, host and port/)).toBeInTheDocument();
    expect(projects.created).toHaveLength(0);
  });

  it("carries the checkbox through when writes are wanted", async () => {
    const projects = new FakeProjectGateway();
    renderProjects(projects);
    await openForm();

    await userEvent.type(screen.getByLabelText("Name"), "Checkout");
    await userEvent.type(screen.getByLabelText("Application origin"), "http://localhost:3000");
    await userEvent.click(screen.getByLabelText(/Let runs click, type and submit/));
    await userEvent.click(screen.getByRole("button", { name: "Create project" }));

    await screen.findByText("Checkout");
    expect(projects.created[0]?.destructiveActions).toBe(true);
  });

  it("shows what the control plane said when it refuses", async () => {
    const projects = new FakeProjectGateway();
    projects.refuse = new Error("origin is not allowed by this deployment");
    renderProjects(projects);
    await openForm();

    await userEvent.type(screen.getByLabelText("Name"), "Checkout");
    await userEvent.type(screen.getByLabelText("Application origin"), "http://localhost:3000");
    await userEvent.click(screen.getByRole("button", { name: "Create project" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "origin is not allowed by this deployment",
    );
  });
});

describe("a project that cannot run says so on its card", () => {
  it("names the missing policy instead of showing an id", async () => {
    // Reachable through the API, and the reason a run would be refused later. The card
    // is the only place a person sees before clicking in.
    const projects = new FakeProjectGateway([
      { projectId: "proj-9", name: "Half made", defaultRunPolicyId: null },
    ]);
    renderProjects(projects);

    expect(await screen.findByText(/no run policy/)).toBeInTheDocument();
  });
});
