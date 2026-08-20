/**
 * The story editor.
 *
 * What it has to get right is not the form mechanics but one warning: a criterion with
 * no text to check for is judged by a model, and a run resting on it can only end
 * `inconclusive`. Saying that while the story is being written is the difference
 * between a deliberate choice and a surprise three runs later (docs/00).
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { UserStory } from "@domain/qa/story";
import type { Gateways } from "@viewmodels/gateways";

import App from "../src/App";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  FakeStoryGateway,
} from "./fakes";

const PROJECT = { projectId: "proj-1", name: "Checkout", defaultRunPolicyId: "pol-1" };

function renderStories(stories: FakeStoryGateway, projects = new FakeProjectGateway([PROJECT])) {
  const gateways: Gateways = {
    projects,
    runs: new FakeRunGateway(),
    events: new FakeRunEventStream(),
    memory: new FakeMemoryGateway(),
    stories,
  };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <MemoryRouter initialEntries={["/projects/proj-1/stories"]}>
      <App gateways={gateways} queryClient={queryClient} />
    </MemoryRouter>,
  );
}

function story(overrides: Partial<UserStory> = {}): UserStory {
  return {
    storyId: "story-1",
    projectId: "proj-1",
    actor: "a signed-in customer",
    goal: "place an order",
    acceptanceCriteria: [
      {
        criterionId: "ac-confirmed",
        description: "the confirmation page appears",
        verificationHint: "Order confirmed",
      },
    ],
    ...overrides,
  };
}

describe("the cost of a criterion with no check is said out loud", () => {
  it("warns while the author is still typing", async () => {
    renderStories(new FakeStoryGateway());

    await userEvent.type(screen.getByLabelText("Id"), "ac-thing");
    await userEvent.type(screen.getByLabelText("Has to be true"), "something happens");

    // The hint is left empty — which is exactly the case the warning is for.
    expect(
      await screen.findByText(/1 of 1 criteria have no text to check for/),
    ).toBeInTheDocument();
  });

  it("says nothing once every criterion has one", async () => {
    renderStories(new FakeStoryGateway());

    await userEvent.type(screen.getByLabelText("Text the page must contain"), "Order confirmed");

    expect(screen.queryByText(/no text to check for/)).not.toBeInTheDocument();
  });

  it("flags a saved story that can never pass or fail", async () => {
    const unverifiable = story({
      acceptanceCriteria: [
        { criterionId: "ac-vague", description: "it feels fast", verificationHint: null },
      ],
    });
    renderStories(new FakeStoryGateway([unverifiable]));

    expect(await screen.findByText(/can only end/)).toBeInTheDocument();
    expect(screen.getByText(/1 judged by a model/)).toBeInTheDocument();
  });
});

describe("saving a story", () => {
  it("sends an absent hint as absent, not as empty text", async () => {
    // The server reads a missing hint as "judge this with a model". Sending "" would
    // be a hint the page can never contain, which is a different and wrong instruction.
    const stories = new FakeStoryGateway();
    renderStories(stories);

    await userEvent.type(screen.getByLabelText("As"), "a customer");
    await userEvent.type(screen.getByLabelText("I want to"), "place an order");
    await userEvent.type(screen.getByLabelText("Id"), "ac-one");
    await userEvent.type(screen.getByLabelText("Has to be true"), "it works");
    await userEvent.click(screen.getByRole("button", { name: "Save story" }));

    await screen.findByText(/As a customer, place an order/);
    expect(stories.drafts[0]?.acceptanceCriteria[0]?.verificationHint).toBeNull();
  });

  it("refuses a story with no acceptance criteria to verify", async () => {
    const stories = new FakeStoryGateway();
    renderStories(stories);

    await userEvent.type(screen.getByLabelText("As"), "a customer");
    await userEvent.type(screen.getByLabelText("I want to"), "place an order");
    await userEvent.click(screen.getByRole("button", { name: "Save story" }));

    // The criterion row is empty, so validation stops it before the gateway is called.
    expect(await screen.findByText("an id the report can point at")).toBeInTheDocument();
    expect(stories.drafts).toHaveLength(0);
  });

  it("rejects a criterion id a report could not point at", async () => {
    const stories = new FakeStoryGateway();
    renderStories(stories);

    await userEvent.type(screen.getByLabelText("As"), "a customer");
    await userEvent.type(screen.getByLabelText("I want to"), "place an order");
    await userEvent.type(screen.getByLabelText("Id"), "Not An Id");
    await userEvent.type(screen.getByLabelText("Has to be true"), "it works");
    await userEvent.click(screen.getByRole("button", { name: "Save story" }));

    expect(await screen.findByText("lowercase letters, digits and dashes")).toBeInTheDocument();
    expect(stories.drafts).toHaveLength(0);
  });
});

describe("compiling", () => {
  it("compiles under the project's policy and moves on to starting a run", async () => {
    // The server refuses a plan with no policy and no budget. Reading the policy from
    // the project keeps one answer to which limits apply (docs/12).
    const stories = new FakeStoryGateway([story()]);
    renderStories(stories);

    await userEvent.click(await screen.findByRole("button", { name: "Compile into a plan" }));

    expect(stories.compiled).toEqual(["story-1@pol-1"]);
    expect(await screen.findByText("Start a run")).toBeInTheDocument();
  });

  it("refuses with a reason when the project has no policy", async () => {
    // Said here rather than sent and bounced as a validation error the reader would
    // have to decode.
    const stories = new FakeStoryGateway([story()]);
    renderStories(
      stories,
      new FakeProjectGateway([{ ...PROJECT, defaultRunPolicyId: null }]),
    );

    expect(await screen.findByText(/no default run policy/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compile into a plan" })).toBeDisabled();
    expect(stories.compiled).toHaveLength(0);
  });
});
