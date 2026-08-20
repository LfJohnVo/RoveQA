"""Agent state carried through the graph.

Kept small on purpose: every field here is checkpointed at each superstep, so a state
that grows with the number of steps makes both the checkpoint and the model context
grow with it. Completed work is summarized into `episode_summaries` and dropped from
`recent_steps` (docs/05 context compaction).

This module is pure domain: no LangGraph, no database, no browser.
"""

from dataclasses import dataclass, field
from enum import StrEnum

MAX_RECENT_STEPS = 12
"""Working window. Older steps survive as summaries, not as raw history."""

MAX_EPISODE_SUMMARIES = 20
"""How many episode summaries stay in context.

Compacting steps into summaries keeps *one* episode flat; without this, a run of two
hundred episodes carries two hundred summaries into every prompt and every checkpoint,
and the thing that grows is the run's duration rather than its work. That is the exact
failure context compaction exists to prevent, one level up.

Older episodes are counted, not kept: the planner is told they happened, and their
durable record is in `run_events` and `criterion_results` where a report reads it.
"""


class StepOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    """Refused by policy: a fact about the run, not a browser malfunction."""


@dataclass(frozen=True)
class StepRecord:
    index: int
    intent: str
    outcome: StepOutcome
    detail: str = ""


@dataclass(frozen=True)
class EpisodeSummary:
    """What an episode achieved, in place of its raw steps."""

    episode_index: int
    goal: str
    steps_taken: int
    succeeded: bool
    summary: str


@dataclass
class AgentState:
    run_id: str
    goal: str
    episode_index: int = 0
    step_index: int = 0
    recent_steps: tuple[StepRecord, ...] = field(default=())
    episode_summaries: tuple[EpisodeSummary, ...] = field(default=())
    folded_episodes: int = 0
    """Episodes that fell out of the summary window.

    A number rather than a synthesised summary: "there were 40 earlier episodes" is
    something the planner can act on, and a fabricated line describing episodes nobody
    kept would be a claim about work no one can check.
    """

    last_observation: str = ""
    pending_action_intent: str | None = None
    goal_reached: bool = False
    failure_reason: str | None = None

    def record_step(self, record: StepRecord) -> None:
        """Append a step and keep only the working window."""
        self.recent_steps = (*self.recent_steps, record)[-MAX_RECENT_STEPS:]
        self.step_index = record.index

    def close_episode(self, summary: EpisodeSummary) -> None:
        """Fold the episode's raw steps into one summary and start the next.

        This is what keeps active context flat: a hundred steps leave a handful of
        summaries behind, not a hundred entries — and past `MAX_EPISODE_SUMMARIES`, the
        oldest summaries become a count, so a long run does not carry its whole history
        into every prompt and every checkpoint.
        """
        summaries = (*self.episode_summaries, summary)
        if len(summaries) > MAX_EPISODE_SUMMARIES:
            self.folded_episodes += len(summaries) - MAX_EPISODE_SUMMARIES
            summaries = summaries[-MAX_EPISODE_SUMMARIES:]
        self.episode_summaries = summaries
        self.recent_steps = ()
        self.episode_index = summary.episode_index + 1

    @property
    def context_size(self) -> int:
        """What a planner would have to read: the window plus the summaries.

        Folded episodes are deliberately not counted. They cost one line between them,
        which is the whole point of folding.
        """
        return len(self.recent_steps) + len(self.episode_summaries)
