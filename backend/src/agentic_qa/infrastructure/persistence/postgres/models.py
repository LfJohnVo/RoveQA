"""SQLAlchemy models. These types never leave infrastructure.

Tables follow docs/11-data-and-artifacts.md and are introduced phase by phase, not
in one mega migration.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from agentic_qa.domain.runs.run import RunStatus, Verdict

IDENTIFIER_LENGTH = 200
NAME_LENGTH = 240


class Base(DeclarativeBase):
    pass


def _string_enum(enum_type: type[StrEnum], name: str) -> Enum:
    """VARCHAR-backed enum: adding a value stays a normal, reviewable migration.

    The value CHECK is declared explicitly in __table_args__ instead of implicitly by
    the type, because autogenerate only matches CHECK constraints it can find by name
    in the metadata — an implicit one looks like drift and gets dropped.
    """
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=False,
        length=20,
        values_callable=lambda enum: [member.value for member in enum],
    )


def _value_check(
    column: str, enum_type: type[StrEnum], name: str, *, nullable: bool
) -> CheckConstraint:
    allowed = ", ".join(f"'{member.value}'" for member in enum_type)
    condition = f"{column} IN ({allowed})"
    if nullable:
        condition = f"{column} IS NULL OR {condition}"
    return CheckConstraint(condition, name=name)


class ProjectModel(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    # No FK: the policy references the project, and a circular FK pair would make
    # both rows impossible to insert first.
    default_run_policy_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RunPolicyModel(Base):
    """Immutable once written: a finished run's rules must not change underneath it."""

    __tablename__ = "run_policies"

    policy_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allowed_origins: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    upload_path_allowlist: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    destructive_actions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_file_uploads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_downloads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synthetic_data_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_actions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_model_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnvironmentModel(Base):
    __tablename__ = "environments"

    environment_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    default_run_policy_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("run_policies.policy_id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserStoryModel(Base):
    __tablename__ = "user_stories"

    story_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordered string lists with no relational query needs: JSONB, not a side table.
    preconditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    forbidden_outcomes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    criteria: Mapped[list["AcceptanceCriterionModel"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="AcceptanceCriterionModel.position",
        lazy="selectin",
    )


class AcceptanceCriterionModel(Base):
    """Criteria are relational: findings and plan steps reference criterion_id."""

    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        UniqueConstraint("story_id", "criterion_id", name="uq_acceptance_criteria_story_criterion"),
        UniqueConstraint("story_id", "position", name="uq_acceptance_criteria_story_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # No separate index: both unique constraints below lead with story_id.
    story_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("user_stories.story_id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    verification_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    story: Mapped[UserStoryModel] = relationship(back_populates="criteria")


class RunEventModel(Base):
    """Durable event journal. Redis Streams are a projection of this, never a source.

    (run_id, sequence) is unique so a concurrent append cannot silently reuse a
    cursor position a client already consumed.
    """

    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),)

    event_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)


class RecoveryPointModel(Base):
    """The domain's safe points (ADR 0009).

    Named `recovery_points`, not `checkpoints`: LangGraph's saver owns a table of that
    exact name, and the two colliding produced a real failure. The distinction is also
    the right one — this table records which graph checkpoint is *semantically* safe
    and how to rebuild the browser there, which is not what a superstep checkpoint is.
    """

    __tablename__ = "recovery_points"

    recovery_point_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    graph_checkpoint_id: Mapped[str] = mapped_column(String(500), nullable=False)
    browser_url: Mapped[str] = mapped_column(Text, nullable=False)
    page_fingerprint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    storage_state_ref: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    last_verified_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TestPlanModel(Base):
    """A compiled, immutable plan version (docs/02, `contracts/test-plan.schema.json`).

    Identity is `(plan_id, plan_version)`: a plan evolves by gaining versions, never by
    being edited, so a finished run can always be read against the rules it ran under.

    The steps live in JSONB rather than a side table on purpose — they are read as a
    whole document, always for one plan version, and no query filters or joins on an
    individual step. `criterion_id` inside them stays queryable through JSONB when a
    report needs it.
    """

    __tablename__ = "test_plans"

    plan_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    plan_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_story_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("user_stories.story_id", ondelete="SET NULL"),
        nullable=True,
    )
    """Provenance. `SET NULL` rather than cascade: deleting the story must not erase the
    plan a finished run was judged by."""

    environment_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("environments.environment_id", ondelete="RESTRICT"),
        nullable=True,
    )
    run_policy_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("run_policies.policy_id", ondelete="RESTRICT"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    memory_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    budget: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    plan_steps: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    plan_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    """The contract calls this `metadata`; `Base.metadata` is taken by SQLAlchemy, so the
    column is renamed here and translated back by the mapper."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CriterionResultModel(Base):
    """One acceptance criterion's outcome for one run (docs/02).

    `model_derived` is a column, not a note in the observation text: a report has to be
    able to show, per row, whether a claim came from a deterministic check or from a
    model's opinion — and a query has to be able to exclude the latter.
    """

    __tablename__ = "criterion_results"
    __table_args__ = (
        UniqueConstraint("run_id", "criterion_id", name="uq_criterion_results_run_criterion"),
        CheckConstraint(
            "outcome IN ('met', 'not_met', 'unverified')", name="ck_criterion_results_outcome"
        ),
        CheckConstraint(
            "(outcome = 'not_met') = (failure_kind IS NOT NULL)",
            name="ck_criterion_results_failure_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    step_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    model_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IdempotencyRecordModel(Base):
    """Durable dedup for repeatable mutations (docs/12). Never Redis-only.

    `resource_id` is deliberately not a foreign key: the scope decides what kind of
    resource it names, and the record is committed in the same transaction as that
    resource, which is what actually guarantees it points at something real.
    """

    __tablename__ = "idempotency_records"

    scope: Mapped[str] = mapped_column(String(100), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RunModel(Base):
    __tablename__ = "runs"
    __table_args__ = (
        _value_check("status", RunStatus, "ck_runs_status", nullable=False),
        _value_check("verdict", Verdict, "ck_runs_verdict", nullable=True),
        # A verdict only exists on terminal runs (docs/02-domain-model.md).
        CheckConstraint(
            "verdict IS NULL OR status IN ('completed', 'failed', 'cancelled')",
            name="ck_runs_verdict_only_when_terminal",
        ),
        # Composite: a run points at one plan *version*, not at a plan.
        ForeignKeyConstraint(
            ["plan_id", "plan_version"],
            ["test_plans.plan_id", "test_plans.plan_version"],
            name="fk_runs_test_plan_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(plan_id IS NULL) = (plan_version IS NULL)",
            name="ck_runs_plan_identity_complete",
        ),
    )

    run_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    run_policy_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("run_policies.policy_id", ondelete="RESTRICT"),
        nullable=True,
    )
    """The policy that governed this run; null only for runs created before Phase 04."""

    environment_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("environments.environment_id", ondelete="RESTRICT"),
        nullable=True,
    )
    plan_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    plan_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Which plan version this run was judged by. Recorded, never re-read from "latest":
    a run finished under version 3 does not become a different result when 4 appears."""

    status: Mapped[RunStatus] = mapped_column(_string_enum(RunStatus, "run_status"), nullable=False)
    verdict: Mapped[Verdict | None] = mapped_column(
        _string_enum(Verdict, "run_verdict"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
