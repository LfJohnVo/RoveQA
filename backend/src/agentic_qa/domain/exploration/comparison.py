"""Comparing today's map of an application against a baseline.

The failure this exists to prevent: a regression report that lists every DOM change and
therefore says nothing. A page whose footer year rolled over, whose table gained a row,
whose order ids are all different — none of that is a change worth waking anyone for,
and a report that includes it teaches its readers to skip it.

So the comparison works on the same normalised states the explorer navigates by. A
state is *new* when its signature was not in the baseline, *gone* when the baseline had
it and this run did not reach it, and *changed* when the same route now offers a
different set of controls. A different value inside a control is not a change here; a
control appearing or disappearing is.

`gone` is reported separately and never merged into the others, because it is the one
finding that can be an artefact of the crawl rather than the application: an
exploration that stopped on budget simply did not get there.
"""

from dataclasses import dataclass, field

from agentic_qa.domain.exploration.state import PageState


@dataclass(frozen=True)
class StateMap:
    """The states one exploration reached, keyed by signature."""

    states: tuple[PageState, ...] = field(default=())
    complete: bool = True
    """False when the exploration stopped on a budget. A comparison against an
    incomplete map cannot tell "removed" from "not reached", and says so."""

    @property
    def by_signature(self) -> dict[str, PageState]:
        return {state.signature: state for state in self.states}

    @property
    def by_route(self) -> dict[str, list[PageState]]:
        grouped: dict[str, list[PageState]] = {}
        for state in self.states:
            grouped.setdefault(state.route, []).append(state)
        return grouped


@dataclass(frozen=True)
class ChangedState:
    """The same route, offering something different."""

    route: str
    baseline_signature: str
    current_signature: str
    gained: tuple[str, ...]
    lost: tuple[str, ...]

    @property
    def summary(self) -> str:
        parts = []
        if self.gained:
            parts.append(f"gained {', '.join(self.gained)}")
        if self.lost:
            parts.append(f"lost {', '.join(self.lost)}")
        return f"{self.route}: {'; '.join(parts)}"


@dataclass(frozen=True)
class MapDelta:
    new: tuple[PageState, ...] = field(default=())
    gone: tuple[PageState, ...] = field(default=())
    changed: tuple[ChangedState, ...] = field(default=())
    unreachable_conclusions: bool = False
    """True when either map was incomplete, so `gone` may be a gap in the crawl rather
    than a removal. Reported rather than suppressed: hiding the finding and hiding its
    caveat are both ways of lying about it."""

    @property
    def has_findings(self) -> bool:
        return bool(self.new or self.gone or self.changed)


def compare(baseline: StateMap, current: StateMap) -> MapDelta:
    """Diff two maps by structure, never by content."""
    baseline_by_signature = baseline.by_signature
    current_by_signature = current.by_signature

    new_signatures = current_by_signature.keys() - baseline_by_signature.keys()
    gone_signatures = baseline_by_signature.keys() - current_by_signature.keys()

    # A route present on both sides with different signatures is one page that changed,
    # not one page that vanished and another that appeared. Resolving that first is
    # what keeps a single added button from being reported as two findings.
    changed = []
    matched_new: set[str] = set()
    matched_gone: set[str] = set()
    current_by_route = current.by_route
    for signature in sorted(gone_signatures):
        before = baseline_by_signature[signature]
        candidates = [
            state
            for state in current_by_route.get(before.route, [])
            if state.signature in new_signatures and state.signature not in matched_new
        ]
        if not candidates:
            continue
        after = min(candidates, key=lambda state: state.signature)
        matched_new.add(after.signature)
        matched_gone.add(signature)
        before_keys = set(before.affordance_keys)
        after_keys = set(after.affordance_keys)
        changed.append(
            ChangedState(
                route=before.route,
                baseline_signature=signature,
                current_signature=after.signature,
                gained=tuple(sorted(after_keys - before_keys)),
                lost=tuple(sorted(before_keys - after_keys)),
            )
        )

    return MapDelta(
        new=tuple(
            current_by_signature[signature] for signature in sorted(new_signatures - matched_new)
        ),
        gone=tuple(
            baseline_by_signature[signature] for signature in sorted(gone_signatures - matched_gone)
        ),
        changed=tuple(changed),
        unreachable_conclusions=not (baseline.complete and current.complete),
    )
