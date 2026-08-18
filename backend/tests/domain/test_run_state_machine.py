"""Run lifecycle invariants (Phase 01 slice 1)."""

import pytest

from agentic_qa.domain.runs.run import (
    TERMINAL_STATUSES,
    Run,
    RunStatus,
    RunTransitionError,
    Verdict,
)


def make_run(status: RunStatus = RunStatus.CREATED) -> Run:
    run = Run(run_id="r-1", project_id="p-1")
    run.status = status
    return run


def test_happy_path_created_to_completed_passed() -> None:
    run = make_run()
    run.transition_to(RunStatus.QUEUED)
    run.transition_to(RunStatus.RUNNING)
    run.transition_to(RunStatus.COMPLETED, Verdict.PASSED)
    assert run.status is RunStatus.COMPLETED
    assert run.verdict is Verdict.PASSED
    assert run.is_terminal


def test_pause_resume_cycle() -> None:
    run = make_run(RunStatus.RUNNING)
    run.transition_to(RunStatus.PAUSING)
    run.transition_to(RunStatus.PAUSED)
    run.transition_to(RunStatus.RUNNING)
    assert run.status is RunStatus.RUNNING
    assert run.verdict is None


def test_recovery_returns_to_running() -> None:
    run = make_run(RunStatus.RUNNING)
    run.transition_to(RunStatus.RECOVERING)
    run.transition_to(RunStatus.RUNNING)
    assert run.status is RunStatus.RUNNING


def test_cancel_flow_forces_cancelled_verdict() -> None:
    run = make_run(RunStatus.RUNNING)
    run.transition_to(RunStatus.CANCELLING)
    run.transition_to(RunStatus.CANCELLED)
    assert run.verdict is Verdict.CANCELLED


def test_any_non_terminal_status_may_fail() -> None:
    for status in RunStatus:
        if status in TERMINAL_STATUSES:
            continue
        run = make_run(status)
        run.transition_to(RunStatus.FAILED)
        assert run.status is RunStatus.FAILED
        assert run.verdict is Verdict.INCONCLUSIVE


def test_failed_accepts_blocked_but_not_qa_verdicts() -> None:
    run = make_run(RunStatus.RUNNING)
    run.transition_to(RunStatus.FAILED, Verdict.BLOCKED)
    assert run.verdict is Verdict.BLOCKED

    run2 = make_run(RunStatus.RUNNING)
    with pytest.raises(RunTransitionError):
        run2.transition_to(RunStatus.FAILED, Verdict.PASSED)


def test_completed_requires_qa_verdict() -> None:
    run = make_run(RunStatus.RUNNING)
    with pytest.raises(RunTransitionError):
        run.transition_to(RunStatus.COMPLETED)
    with pytest.raises(RunTransitionError):
        run.transition_to(RunStatus.COMPLETED, Verdict.CANCELLED)


def test_verdict_rejected_on_non_terminal_transition() -> None:
    run = make_run()
    with pytest.raises(RunTransitionError):
        run.transition_to(RunStatus.QUEUED, Verdict.PASSED)


def test_terminal_states_reject_further_transitions() -> None:
    for status in TERMINAL_STATUSES:
        run = make_run(status)
        with pytest.raises(RunTransitionError):
            run.transition_to(RunStatus.RUNNING)


def test_illegal_skips_are_rejected() -> None:
    run = make_run()
    with pytest.raises(RunTransitionError):
        run.transition_to(RunStatus.RUNNING)  # must queue first
    with pytest.raises(RunTransitionError):
        make_run(RunStatus.CANCELLING).transition_to(RunStatus.RUNNING)
