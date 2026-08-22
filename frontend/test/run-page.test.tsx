/**
 * The run screen, rendered against fake gateways.
 *
 * Two Phase 10 gates live here: a page reload rebuilds the run from REST, and a
 * reconnect does not duplicate rows. Both are rendered rather than asserted on state,
 * because "on screen" is what the gate says and a duplicate row is a rendering fact.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import type { Finding } from "@domain/runs/findings";

import App from "../src/App";
import type { Gateways } from "@viewmodels/gateways";

import {
  FakeMemoryGateway,
  FakeProjectGateway,
  FakeRunEventStream,
  FakeRunGateway,
  makeEvent,
  FakeStoryGateway,
  makeRun,
} from "./fakes";

function renderRun(gateways: Gateways, runId = "run-1") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[`/runs/${runId}`]}>
      <Routes>
        <Route path="*" element={<App gateways={gateways} queryClient={queryClient} />} />
      </Routes>
    </MemoryRouter>,
  );
}

function gatewaysWith(runs: FakeRunGateway, events: FakeRunEventStream): Gateways {
  return { projects: new FakeProjectGateway(), runs, events, memory: new FakeMemoryGateway(), stories: new FakeStoryGateway() };
}

function timelineRows(): HTMLElement[] {
  // By role and accessible name rather than by class: a query tied to `.timeline__row`
  // breaks the moment the timeline is restyled, which says nothing about the timeline.
  const timeline = screen.queryByRole("table", { name: "Timeline" });
  return timeline === null ? [] : within(timeline).getAllByRole("row").slice(1);
}

describe("a reload rebuilds the run from the durable log", () => {
  it("shows events that happened before the page existed", async () => {
    // Nothing arrives over the socket here. Everything on screen came from REST, which
    // is exactly the situation after F5 halfway through a long run.
    const runs = new FakeRunGateway(makeRun(), [makeEvent(1), makeEvent(2), makeEvent(3)]);
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await waitFor(() => expect(timelineRows()).toHaveLength(3));
    expect(screen.getByText("3 events")).toBeInTheDocument();
  });

  it("shows the durable status, not a guess from the URL", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "paused" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await waitFor(() => expect(screen.getByText("paused")).toBeInTheDocument());
  });
});

describe("a reconnect does not duplicate rows", () => {
  it("keeps one row when the catch-up overlaps the live feed", async () => {
    const runs = new FakeRunGateway(makeRun(), [makeEvent(1), makeEvent(2)]);
    const events = new FakeRunEventStream();
    renderRun(gatewaysWith(runs, events));

    await waitFor(() => expect(timelineRows()).toHaveLength(2));

    // The socket drops and comes back replaying from a sequence the screen already has.
    events.setConnection("reconnecting");
    events.setConnection("live");
    events.deliver(makeEvent(2), makeEvent(3));

    await waitFor(() => expect(timelineRows()).toHaveLength(3));
    const sequences = timelineRows().map((row) => row.textContent?.slice(0, 1));
    expect(sequences).toEqual(["1", "2", "3"]);
  });

  it("says so while it is not live", async () => {
    const runs = new FakeRunGateway(makeRun());
    const events = new FakeRunEventStream();
    renderRun(gatewaysWith(runs, events));

    await waitFor(() => expect(screen.getByRole("status", { name: "" })).toBeDefined());
    events.setConnection("reconnecting");

    // A console that looks identical live and stalled invites acting on a stale picture.
    await waitFor(() =>
      expect(screen.getByText(/showing the last durable state/)).toBeInTheDocument(),
    );
  });
});

describe("lifecycle commands", () => {
  it("offers pause for a running run and sends it", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "running" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const pause = await screen.findByRole("button", { name: "Pause" });
    await userEvent.click(pause);

    await waitFor(() => expect(runs.commands).toEqual(["pause"]));
  });

  it("does not offer pause for a run that already finished", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const pause = await screen.findByRole("button", { name: "Pause" });
    expect(pause).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });

  it("offers resume instead of pause when the run is paused", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "paused" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await waitFor(() => expect(screen.getByRole("button", { name: "Resume" })).toBeEnabled());
    expect(screen.getByRole("button", { name: "Pause" })).toBeDisabled();
  });
});

describe("a verdict reads as what it means", () => {
  it("does not colour an inconclusive run as a failure", async () => {
    // "The run could not tell" is not "your product is broken", and colour is the
    // fastest way to say the wrong one.
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "inconclusive" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const badge = await screen.findByText("inconclusive");
    expect(badge).toHaveAttribute("data-tone", "no-answer");
  });

  it("marks a failed run as an answer about the product", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "failed" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const badge = await screen.findByText("failed");
    expect(badge).toHaveAttribute("data-tone", "answer-fail");
  });
});

describe("projects", () => {
  it("lists what the control plane knows", async () => {
    const gateways: Gateways = {
      projects: new FakeProjectGateway([
        { projectId: "proj-1", name: "Checkout", defaultRunPolicyId: "pol-1" },
      ]),
      runs: new FakeRunGateway(),
      events: new FakeRunEventStream(),
      memory: new FakeMemoryGateway(),
      stories: new FakeStoryGateway(),
    };
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <MemoryRouter initialEntries={["/projects"]}>
        <App gateways={gateways} queryClient={queryClient} />
      </MemoryRouter>,
    );

    // Awaiting the text, not the list: the empty <ul> is on screen from the first
    // render, so finding it proves only that the page mounted.
    const name = await screen.findByText("Checkout");
    expect(name.closest("a")).toHaveAttribute("href", "/projects/proj-1");
  });

  it("says a project does not exist rather than showing a broken screen", async () => {
    const gateways: Gateways = {
      projects: new FakeProjectGateway([]),
      runs: new FakeRunGateway(),
      events: new FakeRunEventStream(),
      memory: new FakeMemoryGateway(),
      stories: new FakeStoryGateway(),
    };
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <MemoryRouter initialEntries={["/projects/nope"]}>
        <App gateways={gateways} queryClient={queryClient} />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No such project")).toBeInTheDocument();
  });
});

describe("the screen follows the run's real status", () => {
  it("re-reads the run when a status event arrives", async () => {
    // The event says something changed; the durable resource says what it is now.
    // Taking the status from the payload would make the screen depend on which events
    // happened to arrive.
    const runs = new FakeRunGateway(makeRun({ status: "running" }));
    const events = new FakeRunEventStream();
    renderRun(gatewaysWith(runs, events));

    await screen.findByText("running");

    runs.setStatus("paused");
    events.deliver(makeEvent(1, "run.status.changed"));

    expect(await screen.findByText("paused")).toBeInTheDocument();
  });

  it("stops watching once the run is finished", async () => {
    // A socket retrying against a run that will never speak again shows
    // "reconnecting" forever on a screen that is simply history.
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    const events = new FakeRunEventStream();
    renderRun(gatewaysWith(runs, events));

    await screen.findByText("passed");
    expect(events.subscriptions).toBe(0);
    expect(screen.getByText(/nothing more to receive/)).toBeInTheDocument();
  });

  it("closes the feed when a run finishes while being watched", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "running" }));
    const events = new FakeRunEventStream();
    renderRun(gatewaysWith(runs, events));

    await screen.findByText("running");

    runs.run = makeRun({ status: "completed", verdict: "failed" });
    events.deliver(makeEvent(1, "run.status.changed"));

    expect(await screen.findByText("failed")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/nothing more to receive/)).toBeInTheDocument(),
    );
  });
});

describe("findings keep observations and hypotheses apart", () => {
  function withReport(findings: Finding[]) {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "failed" }));
    runs.reportValue = {
      runId: "run-1",
      findings,
      observed: [],
      artifacts: [],
      evidenceSetId: "ev-1",
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));
  }

  const base: Finding = {
    criterionId: "ac-checkout",
    source: "plan",
    stepId: "step-1",
    outcome: "not_met",
    failureKind: "product",
    deterministicObservation: null,
    rootCauseHypothesis: null,
    modelDerived: false,
    modelName: null,
  };

  it("colours a deterministic product failure as an answer about the product", async () => {
    withReport([{ ...base, deterministicObservation: "no confirmation appeared" }]);

    const badge = await screen.findByText("not met");
    expect(badge).toHaveAttribute("data-tone", "answer-fail");
    expect(screen.getByText("no confirmation appeared")).toBeInTheDocument();
  });

  it("does not colour a plan or environment failure as a defect", async () => {
    // The run failed to establish anything. Saying the product is broken would be a
    // different — and wrong — claim.
    withReport([
      { ...base, failureKind: "environment", deterministicObservation: "target unreachable" },
    ]);

    const badge = await screen.findByText("not met");
    expect(badge).toHaveAttribute("data-tone", "no-answer");
  });

  it("labels a model hypothesis as one and names the model", async () => {
    withReport([
      {
        ...base,
        outcome: "unverified",
        failureKind: null,
        rootCauseHypothesis: "the button may be hidden behind a modal",
        modelDerived: true,
        modelName: "qwen",
      },
    ]);

    expect(await screen.findByText(/hypothesis · qwen/)).toBeInTheDocument();
    expect(screen.getByText(/may be hidden behind a modal/)).toBeInTheDocument();
  });

  it("counts only product failures as accusations", async () => {
    withReport([
      { ...base, failureKind: "product", deterministicObservation: "a real defect" },
      { ...base, criterionId: "ac-other", failureKind: "plan", deterministicObservation: "vague" },
    ]);

    expect(await screen.findByText("1 accusing the product")).toBeInTheDocument();
  });

  it("asks for no report while the run is still going", async () => {
    // A report fetched mid-run is empty, and refetching it on every status change is
    // load with no answer attached.
    const runs = new FakeRunGateway(makeRun({ status: "running" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await screen.findByText("running");
    expect(screen.queryByText("Findings")).not.toBeInTheDocument();
  });
});

describe("what the browser saw is not what the run concluded", () => {
  it("shows console errors and failed requests in their own section", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    runs.reportValue = {
      runId: "run-1",
      findings: [],
      observed: [
        { kind: "console_error", detail: "TypeError: x is not a function", episodeIndex: 0 },
        { kind: "failed_request", detail: "https://cdn.test/logo.png", episodeIndex: 1 },
      ],
      artifacts: [],
      evidenceSetId: "ev-1",
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const table = await screen.findByRole("table", { name: "What the browser saw" });
    expect(within(table).getByText("TypeError: x is not a function")).toBeInTheDocument();
    expect(within(table).getByText("https://cdn.test/logo.png")).toBeInTheDocument();
  });

  it("says out loud that none of them is a verdict", async () => {
    // A reader who takes a noisy console for a failing test is a reader who stops
    // trusting the report — in either direction.
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    runs.reportValue = {
      runId: "run-1",
      findings: [],
      observed: [{ kind: "console_error", detail: "boom", episodeIndex: 0 }],
      artifacts: [],
      evidenceSetId: null,
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    expect(await screen.findByText(/none of them is a verdict/)).toBeInTheDocument();
    // The run still reads as passed. An observation cannot change that.
    expect(screen.getByText("passed")).toBeInTheDocument();
  });

  it("shows nothing at all when the browser saw nothing", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await screen.findByText("passed");
    expect(screen.queryByRole("table", { name: "What the browser saw" })).toBeNull();
  });
});

describe("a traversal shows what it mapped", () => {
  it("draws the states it reached", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    runs.explorationValue = {
      runId: "run-1",
      states: [
        { signature: "s1", route: "/", url: "https://app.test/", title: "Home", affordances: [] },
        {
          signature: "s2",
          route: "/about",
          url: "https://app.test/about",
          title: "About",
          affordances: ["link:home"],
        },
      ],
      stopReason: "frontier_exhausted",
      complete: true,
      statesDiscovered: 2,
      actionsTaken: 2,
      declined: 0,
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    const map = await screen.findByRole("img", { name: /Map of 2 states/ });
    expect(within(map).getByText("/about")).toBeInTheDocument();
  });

  it("says when the map has holes rather than letting it read as complete", async () => {
    // A map that stopped on a budget and one that ran out of places to go look identical.
    // Only the second supports "this page is gone" next time.
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    runs.explorationValue = {
      runId: "run-1",
      states: [
        { signature: "s1", route: "/", url: "https://app.test/", title: "Home", affordances: [] },
      ],
      stopReason: "max_actions",
      complete: false,
      statesDiscovered: 1,
      actionsTaken: 6,
      declined: 3,
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    expect(await screen.findByText(/what it reached rather than everything/)).toBeInTheDocument();
    expect(screen.getByText(/3 controls left alone/)).toBeInTheDocument();
  });

  it("shows nothing at all for a run that never explored", async () => {
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await screen.findByText("passed");
    expect(screen.queryByRole("img", { name: /Map of/ })).toBeNull();
  });
});

describe("a healthy run does not look broken", () => {
  it("does not raise an alert because there is no failure to bundle", async () => {
    // A run that passed has no failure context, and the server says so with a 404. That
    // put a red alert on every healthy run's page: the screen crying wolf about the
    // absence of a problem. Seen on a real report before anyone reported it.
    const runs = new FakeRunGateway(makeRun({ status: "completed", verdict: "passed" }));
    runs.reportValue = {
      runId: "run-1",
      findings: [],
      observed: [],
      artifacts: [],
      evidenceSetId: null,
    };
    renderRun(gatewaysWith(runs, new FakeRunEventStream()));

    await screen.findByText("passed");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
