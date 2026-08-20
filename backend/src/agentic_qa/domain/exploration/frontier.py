"""The frontier, and the budgets that make an exploration end.

An explorer that cannot stop is not a feature, it is an outage with a progress bar. So
termination here is structural rather than hopeful:

- every affordance is offered **once** — taking it moves it out of the frontier for
  good, whether it led somewhere new, somewhere already visited, or nowhere;
- a state's affordances are enqueued **once**, the first time the state is seen;
- states are capped, actions are capped, depth prunes, and the clock is checked.

Together those mean the frontier is finite and strictly consumed, so the loop ends even
if every budget is generous and every page links to every other page. The budgets bound
*how long* it takes; the structure is what guarantees it happens at all.

Nothing here reads a clock or a database. Elapsed time arrives as a number, because a
domain that calls `now()` cannot be replayed and cannot be tested without waiting.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.projects.run_policy import RunPolicy

DEFAULT_MAX_STATES = 50


class StopReason(StrEnum):
    GOAL_REACHED = "goal_reached"
    FRONTIER_EXHAUSTED = "frontier_exhausted"
    """Everything reachable within the budget was reached. The only stop reason that
    means the exploration is *complete* rather than merely finished."""

    MAX_ACTIONS = "max_actions"
    MAX_STATES = "max_states"
    DEADLINE = "deadline"


@dataclass(frozen=True)
class ExplorationBudget:
    """What one exploration may spend.

    Never wider than the RunPolicy that governs the run — `under()` is the only
    intended way to build one. Exploration is a way of using a run's allowance, not a
    second allowance beside it, and a budget that could exceed the policy would make
    the policy advisory.
    """

    max_actions: int
    max_states: int
    max_depth: int
    max_duration_seconds: float

    def __post_init__(self) -> None:
        for name, value in (
            ("max_actions", self.max_actions),
            ("max_states", self.max_states),
            ("max_duration_seconds", self.max_duration_seconds),
        ):
            if value < 1:
                raise InvalidEntityError(f"{name} must be at least 1")
        if self.max_depth < 0:
            raise InvalidEntityError("max_depth must not be negative")

    @classmethod
    def under(
        cls, policy: RunPolicy, *, max_states: int = DEFAULT_MAX_STATES, default_depth: int = 4
    ) -> "ExplorationBudget":
        """Clamp to the policy. A policy with no depth limit still gets one here:
        unbounded depth is how an explorer walks into pagination and never returns."""
        return cls(
            max_actions=policy.max_actions,
            max_states=max_states,
            max_depth=policy.max_depth if policy.max_depth is not None else default_depth,
            max_duration_seconds=float(policy.max_duration_seconds),
        )


@dataclass(frozen=True)
class ExplorationProgress:
    """Everything the stop decision is allowed to look at."""

    actions_taken: int
    states_discovered: int
    elapsed_seconds: float
    frontier_size: int
    goal_reached: bool = False


def stop_reason(budget: ExplorationBudget, progress: ExplorationProgress) -> StopReason | None:
    """Why exploration should stop now, or None to continue.

    Ordered by what a reader most needs to know. "We found what we came for" and "we
    ran out of places to go" are outcomes; the budget reasons are interruptions, and
    conflating them would make a truncated crawl read like a complete one.
    """
    if progress.goal_reached:
        return StopReason.GOAL_REACHED
    if progress.elapsed_seconds >= budget.max_duration_seconds:
        return StopReason.DEADLINE
    if progress.actions_taken >= budget.max_actions:
        return StopReason.MAX_ACTIONS
    if progress.states_discovered >= budget.max_states:
        return StopReason.MAX_STATES
    if progress.frontier_size == 0:
        return StopReason.FRONTIER_EXHAUSTED
    return None


@dataclass(frozen=True)
class FrontierEntry:
    """One thing left to try, and where from."""

    state_signature: str
    affordance: Affordance
    depth: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.state_signature, self.affordance.key)


@dataclass(frozen=True)
class FrontierSnapshot:
    """A frontier flattened into tuples so a checkpoint can hold it.

    An exploration is exactly the kind of long run that must survive a worker dying, so
    the frontier cannot live only in process memory. Tuples rather than the live object
    because what goes into a checkpoint has to be reconstructible from an allowlisted
    set of plain types.
    """

    visited: tuple[PageState, ...] = field(default=())
    depths: tuple[tuple[str, int], ...] = field(default=())
    pending: tuple[FrontierEntry, ...] = field(default=())
    offered: tuple[tuple[str, str], ...] = field(default=())
    actions_taken: int = 0
    declined: int = 0


@dataclass(frozen=True)
class ExplorationReport:
    """What the run spent and what it found. Rendered for a human, read by a diff."""

    stop_reason: StopReason
    actions_taken: int
    states_discovered: int
    max_depth_reached: int
    frontier_remaining: int
    budget: ExplorationBudget | None = None
    """The budget it explored under, when the report is fresh.

    Absent on a report read back from storage: the budget is a property of the run's
    policy, which is already durable and already pinned onto the run, so a stored copy
    would be a second version free to disagree with the first."""
    declined: int = 0
    """Affordances the run was not allowed to take.

    Counted rather than attempted, and reported rather than hidden: "mapped 12 states,
    left 4 controls alone because this run may not change anything" is a different
    statement from "mapped 12 states", and only one of them lets a reader decide
    whether to run it again with a wider policy.
    """

    @property
    def complete(self) -> bool:
        """Whether everything reachable was reached. False means the map has holes,
        and a comparison against it must not read a missing state as a removed one."""
        return self.stop_reason in (StopReason.FRONTIER_EXHAUSTED, StopReason.GOAL_REACHED)


class Frontier:
    """Visited states and what is left to try, with depth.

    Deliberately a plain object with no I/O: an exploration has to be replayable from a
    checkpoint, and a frontier that reached for a database could not be rebuilt from
    one.
    """

    def __init__(
        self,
        budget: ExplorationBudget,
        *,
        takeable: Callable[[Affordance], bool] | None = None,
    ) -> None:
        self._budget = budget
        self._takeable = takeable if takeable is not None else _clickable
        """What this run may actually take. Applied at enqueue time, because a denied
        action ends an episode by design — so an explorer must never queue one."""

        self._declined = 0
        self._visited: dict[str, PageState] = {}
        self._depth: dict[str, int] = {}
        self._pending: list[FrontierEntry] = []
        self._offered: set[tuple[str, str]] = set()
        """Every affordance ever handed out. An affordance is offered once and never
        again — that is what stops two pages linking to each other from becoming an
        infinite walk."""

        self._actions_taken = 0

    @property
    def visited(self) -> tuple[PageState, ...]:
        return tuple(self._visited.values())

    @property
    def states_discovered(self) -> int:
        return len(self._visited)

    @property
    def actions_taken(self) -> int:
        return self._actions_taken

    @property
    def pending(self) -> tuple[FrontierEntry, ...]:
        return tuple(self._pending)

    @property
    def max_depth_reached(self) -> int:
        return max(self._depth.values(), default=0)

    @property
    def declined(self) -> int:
        return self._declined

    def snapshot(self) -> FrontierSnapshot:
        return FrontierSnapshot(
            visited=tuple(self._visited.values()),
            depths=tuple(self._depth.items()),
            pending=tuple(self._pending),
            offered=tuple(sorted(self._offered)),
            actions_taken=self._actions_taken,
            declined=self._declined,
        )

    @classmethod
    def from_snapshot(
        cls,
        budget: ExplorationBudget,
        snapshot: FrontierSnapshot | None,
        *,
        takeable: Callable[[Affordance], bool] | None = None,
    ) -> "Frontier":
        """Rebuild a frontier mid-exploration. `None` starts a fresh one.

        `offered` is restored too, and that is the important part: without it a resumed
        exploration would re-offer everything it had already tried and could walk a
        two-page cycle forever, having survived the crash and lost the guarantee.
        """
        frontier = cls(budget, takeable=takeable)
        if snapshot is None:
            return frontier
        frontier._visited = {state.signature: state for state in snapshot.visited}
        frontier._depth = dict(snapshot.depths)
        frontier._pending = list(snapshot.pending)
        frontier._offered = set(snapshot.offered)
        frontier._actions_taken = snapshot.actions_taken
        frontier._declined = snapshot.declined
        return frontier

    def has_seen(self, state: PageState) -> bool:
        return state.signature in self._visited

    def record(self, state: PageState, *, depth: int = 0) -> bool:
        """Register a state. True when it had never been seen before.

        Its affordances are enqueued only on that first sighting: re-enqueuing them on
        every arrival would refill the frontier as fast as it drains, which is the same
        infinite loop written a different way.
        """
        signature = state.signature
        if signature in self._visited:
            # Arriving again by a shorter path is worth recording — depth is what the
            # prune reads — but it does not reopen the state for exploration.
            self._depth[signature] = min(self._depth[signature], depth)
            return False

        self._visited[signature] = state
        self._depth[signature] = depth
        if depth < self._budget.max_depth:
            self._enqueue(state, depth=depth + 1)
        return True

    def _enqueue(self, state: PageState, *, depth: int) -> None:
        signature = state.signature
        for affordance in state.affordances:
            if not self._takeable(affordance):
                # A textbox still counts towards the state's identity; it is not
                # something to walk through. Nor is a control this run may not touch.
                self._declined += 1
                continue
            entry = FrontierEntry(state_signature=signature, affordance=affordance, depth=depth)
            if entry.key in self._offered:
                continue
            self._offered.add(entry.key)
            self._pending.append(entry)
        # Shallowest first, then by affordance key: breadth before depth finds the
        # shape of an application sooner, and the tiebreak keeps two runs over the same
        # site in the same order.
        self._pending.sort(key=lambda item: (item.depth, item.affordance.key))

    def take(self) -> FrontierEntry | None:
        """Hand out the next thing to try, permanently removing it from the frontier."""
        if not self._pending:
            return None
        entry = self._pending.pop(0)
        self._actions_taken += 1
        return entry

    def depth_of(self, state: PageState) -> int:
        return self._depth.get(state.signature, 0)

    def progress(
        self, *, elapsed_seconds: float, goal_reached: bool = False
    ) -> ExplorationProgress:
        return ExplorationProgress(
            actions_taken=self._actions_taken,
            states_discovered=len(self._visited),
            elapsed_seconds=elapsed_seconds,
            frontier_size=len(self._pending),
            goal_reached=goal_reached,
        )

    def report(self, reason: StopReason) -> ExplorationReport:
        return ExplorationReport(
            stop_reason=reason,
            actions_taken=self._actions_taken,
            states_discovered=len(self._visited),
            max_depth_reached=self.max_depth_reached,
            frontier_remaining=len(self._pending),
            budget=self._budget,
            declined=self._declined,
        )


def _clickable(affordance: Affordance) -> bool:
    """Default when no policy is supplied: anything a click could take.

    Used by tests and by any caller exploring a model of a site rather than a real one.
    A real run passes a predicate built from its RunPolicy.
    """
    return affordance.is_clickable
