"""What grows with a run's work, and what must not grow with its length.

A multi-hour run is only possible if the cost of taking one more step is the same at
step 5000 as at step 5. Three things sit on that path and all three are measured here:
the state a checkpoint carries, the prompt a planner reads, and the count of things a
report has to reconcile.

The measurement is a ratio, not an absolute. Absolute byte counts drift with every
wording change and would make this file a maintenance tax that people delete; "twenty
times the episodes costs less than twice the state" is the property, and it survives
rewording.

Writing this found the leak it was written to look for: episode summaries were unbounded,
so a two-hundred-episode run carried two hundred of them into every prompt and every
checkpoint. That is growth with duration wearing the costume of compaction.
"""

import pickle

from agentic_qa.application.ports.models import PlanningRequest
from agentic_qa.domain.agent.state import (
    MAX_EPISODE_SUMMARIES,
    MAX_RECENT_STEPS,
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.infrastructure.inference.prompts import build_planning_prompt


def run_for(*, episodes: int, steps_per_episode: int = 30) -> AgentState:
    """A run that did real work: many episodes, each with many steps."""
    agent = AgentState(run_id="run-1", goal="exercise the whole application")
    for episode in range(episodes):
        for step in range(steps_per_episode):
            agent.record_step(
                StepRecord(
                    index=step,
                    intent=f"do the thing {step}",
                    outcome=StepOutcome.SUCCEEDED,
                    detail="it worked as expected",
                )
            )
        agent.close_episode(
            EpisodeSummary(
                episode_index=episode,
                goal=f"episode {episode}",
                steps_taken=steps_per_episode,
                succeeded=True,
                summary="everything the episode did, in one line",
            )
        )
    return agent


def state_bytes(agent: AgentState) -> int:
    """What a checkpoint has to carry.

    Pickle rather than the real serializer: this measures the *shape* of the state, and
    a comparison between two states of the same shape is unaffected by which encoder
    writes them.
    """
    return len(pickle.dumps(agent))


def prompt_for(agent: AgentState) -> str:
    return build_planning_prompt(
        PlanningRequest(
            goal=agent.goal,
            observation="a page with some controls on it",
            recent_steps=agent.recent_steps,
            episode_summaries=agent.episode_summaries,
            folded_episodes=agent.folded_episodes,
        )
    )


class TestTheStateACheckpointCarries:
    def test_it_does_not_grow_with_the_number_of_steps(self) -> None:
        short = state_bytes(run_for(episodes=1, steps_per_episode=10))
        long = state_bytes(run_for(episodes=1, steps_per_episode=5_000))

        # The working window is the same size either way, so the states are within
        # noise of each other.
        assert long < short * 1.2

    def test_it_does_not_grow_with_the_number_of_episodes(self) -> None:
        # The leak this file found: without a bound on summaries, twenty times the
        # episodes was twenty times the state, in every checkpoint of every superstep.
        few = state_bytes(run_for(episodes=10))
        many = state_bytes(run_for(episodes=200))

        assert many < few * 2

    def test_the_summary_window_is_what_bounds_it(self) -> None:
        agent = run_for(episodes=200)

        assert len(agent.episode_summaries) == MAX_EPISODE_SUMMARIES
        assert len(agent.recent_steps) <= MAX_RECENT_STEPS
        assert agent.folded_episodes == 200 - MAX_EPISODE_SUMMARIES


class TestThePromptAPlannerReads:
    def test_it_stops_growing_once_the_window_is_full(self) -> None:
        """Both of these are past the window, and that is the point.

        A prompt does grow while the first summaries accumulate — twenty of them is the
        budget. What must not happen is the two-hundredth episode costing more than the
        twentieth, and the thousandth more than that.
        """
        full = len(prompt_for(run_for(episodes=MAX_EPISODE_SUMMARIES)))
        longer = len(prompt_for(run_for(episodes=200)))
        much_longer = len(prompt_for(run_for(episodes=1_000)))

        # The only difference between them is the digits in "N earlier episodes".
        assert longer < full * 1.1
        assert much_longer < full * 1.1

    def test_a_thousand_episode_run_still_produces_a_readable_prompt(self) -> None:
        prompt = prompt_for(run_for(episodes=1_000, steps_per_episode=5))

        # A ceiling a person can hold in their head, and one a model can afford.
        assert len(prompt) < 20_000

    def test_the_planner_is_told_the_history_it_sees_is_partial(self) -> None:
        """Otherwise it would read a partial history as a complete one and conclude it
        had never tried something it tried forty episodes ago."""
        prompt = prompt_for(run_for(episodes=200))

        assert f"{200 - MAX_EPISODE_SUMMARIES} earlier episode(s), no longer shown" in prompt

    def test_a_short_run_says_nothing_about_folding(self) -> None:
        # Nothing was folded, so claiming otherwise would be noise in every early prompt.
        assert "no longer shown" not in prompt_for(run_for(episodes=3))


class TestWhatIsAllowedToGrow:
    def test_the_episode_index_still_counts_every_episode(self) -> None:
        """Folding is about context, not about forgetting. The run still knows how far
        it got, and the durable record of each episode is in `run_events`."""
        agent = run_for(episodes=200)

        assert agent.episode_index == 200

    def test_context_size_reports_what_a_planner_reads(self) -> None:
        agent = run_for(episodes=200)

        # Folded episodes cost one line between them, so they are not context.
        assert agent.context_size == len(agent.episode_summaries)
        assert agent.context_size <= MAX_EPISODE_SUMMARIES + MAX_RECENT_STEPS
