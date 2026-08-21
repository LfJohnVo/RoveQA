"""Turning something a page offers into an action, safely.

The rule this file exists to enforce: **exploration widens nothing.** An explorer takes
only what the run's policy already allows a planner to take, and it finds that out by
asking the same guard, with the same action, that every other action goes through. A
second set of rules for exploration would be a second place for them to disagree.

The consequence is worth stating plainly. A link whose destination the page told us is
followed by *navigating*, which is read-only, so an exploration can map an application
under a policy that forbids changing it. A button can only be clicked, and clicking an
unknown control can place an order — so under a read-only policy buttons are simply not
offered. They are counted, not attempted.
"""

from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.browser.policy_guard import evaluate_action
from agentic_qa.domain.exploration.state import Affordance
from agentic_qa.domain.projects.run_policy import RunPolicy


def exploration_action(affordance: Affordance) -> BrowserAction:
    """The safest action that takes this affordance.

    The choice itself lives on `Affordance.reached_by`, so the observation shown to a
    planner and the action an explorer builds cannot disagree about it.
    """
    if affordance.reached_by == "navigate" and affordance.url:
        return BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent=f"explore {affordance.role} {affordance.name}",
            target=ActionTarget(url=affordance.url),
        )
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent=f"explore {affordance.role} {affordance.name}",
        target=ActionTarget(role=affordance.role, name=affordance.name),
        side_effect=True,
        # The effect is unknown by definition, so retrying blindly is not allowed:
        # what happened has to be looked at first (ADR 0009).
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="observe the page after the click",
    )


def is_takeable(affordance: Affordance, policy: RunPolicy) -> bool:
    """Whether this run may take this affordance at all.

    Asked *before* the affordance enters the frontier, which is the difference between
    a useful read-only exploration and one that dies at the first button. A denied
    action ends an episode by design — that is what stops an agent from hunting for a
    way around a policy — so an explorer must never queue one. It is not being
    permissive: the same guard, the same answer, one step earlier.
    """
    if not affordance.is_clickable:
        return False
    return evaluate_action(exploration_action(affordance), policy).allowed
