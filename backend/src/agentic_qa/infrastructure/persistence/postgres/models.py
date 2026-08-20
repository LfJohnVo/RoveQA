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
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
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


class ArtifactModel(Base):
    """A reference to one captured artifact. The bytes stay on the filesystem.

    docs/11 is explicit that operational tables hold references, not screenshots: a
    row here is identity, provenance and integrity (hash, size), and the blob lives
    where blobs belong.

    `evidence_set_id` is a column rather than an inference, because the rule a failure
    bundle must enforce — one run, one evidence set — can only be checked against
    something that was recorded at capture time.
    """

    __tablename__ = "artifacts"
    __table_args__ = (UniqueConstraint("run_id", "relative_path", name="uq_artifacts_run_path"),)

    artifact_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_set_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
    model_invocation_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeCandidateModel(Base):
    """Durable knowledge (ADR 0008). FalkorDB holds a projection of this, not the truth.

    `dedup_key` is what makes a second run's agreement add support instead of adding a
    row: the same fact, in the same scope and context, has one identity. Without it,
    "how many runs agree" — the number promotion depends on — could not be answered.

    Scope columns lead because retrieval filters on them *before* ranking: memory from
    another project or environment is not weaker evidence, it is evidence about
    something else.
    """

    __tablename__ = "knowledge_candidates"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "environment_id", "dedup_key", name="uq_knowledge_candidates_dedup"
        ),
        CheckConstraint("observed OR model_derived", name="ck_knowledge_candidates_has_a_source"),
        # The rule the whole design rests on, defended by the database too.
        CheckConstraint(
            "NOT (model_derived AND status = 'trusted')",
            name="ck_knowledge_candidates_model_derived_never_trusted",
        ),
        CheckConstraint(
            "reliability >= 0 AND reliability <= 1", name="ck_knowledge_candidates_reliability"
        ),
        # The retrieval query, in order: scope, then what is actionable, then the
        # ranking. A separate index on project_id alone would be a prefix of this one
        # and earn nothing but write cost.
        Index(
            "ix_knowledge_candidates_retrieval",
            "project_id",
            "environment_id",
            "status",
            desc("reliability"),
        ),
    )

    candidate_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    environment_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_derived: Mapped[bool] = mapped_column(Boolean, nullable=False)

    source_run_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    source_episode_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    evidence_set_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    test_plan_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_invocation_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_fingerprint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)

    support_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    """Stored so retrieval can order by it in SQL. Always recomputed from the counts,
    never set independently of them."""

    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemoryFeedbackModel(Base):
    """What later runs discovered about knowledge they used.

    The unique key is the whole point: an episode that retries after a lost
    acknowledgement must not report its outcome twice. Reliability is a count of
    independent outcomes, and a retry is not one of those.

    Rows are kept after the candidate they judge is invalidated — the evidence that
    something stopped being true is worth as much as the fact was (docs/26).
    """

    __tablename__ = "memory_feedback"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "run_id",
            "episode_id",
            "kind",
            name="uq_memory_feedback_occurrence",
        ),
        Index("ix_memory_feedback_candidate", "candidate_id", "created_at"),
    )

    feedback_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("knowledge_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    episode_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False, default="")
    """Empty string rather than NULL: PostgreSQL treats NULLs in a unique constraint as
    distinct, so a nullable column here would let the same retry insert twice."""

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    observed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GraphSyncStateModel(Base):
    """Whether a durable candidate has reached the graph projection.

    Separate from the candidate's status on purpose. The graph being down says nothing
    about whether the knowledge is true, so an outage must not be able to demote a
    promoted fact — and a run must never fail because a projection lagged (ADR 0008).

    This table is also what makes `memory rebuild` possible: it names exactly what the
    graph is missing, so recovery does not mean re-running anybody's tests.
    """

    __tablename__ = "graph_sync_state"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'synced', 'failed')", name="ck_graph_sync_state_known_state"
        ),
        # The rebuild/backlog query: what still has to reach the graph, oldest first.
        Index("ix_graph_sync_state_backlog", "state", "updated_at"),
    )

    candidate_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("knowledge_candidates.candidate_id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    graph_schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """Which projection shape the node was written under. A schema change makes every
    row that names an older version a rebuild target instead of a silent mismatch."""

    graph_node_id: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
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


class FailureClusterModel(Base):
    """One deterministic failure cluster for a project (Phase 11).

    Identity is `(project_id, cluster_id)` and the cluster id is derived from the
    grouping key, so re-running triage over a wider batch finds the same row and adds
    members to it instead of creating a second copy of the same problem. That is what
    makes the analysis pass safe to retry.

    Nothing here is model-derived. The hypothesis lives in its own table with its own
    row lifecycle, so writing one cannot touch the members or the reason that justify
    the cluster.
    """

    __tablename__ = "failure_clusters"
    __table_args__ = (
        UniqueConstraint("project_id", "cluster_id", name="uq_failure_clusters_identity"),
        CheckConstraint(
            "status IN ('independent', 'blocked_downstream')", name="ck_failure_clusters_status"
        ),
        CheckConstraint(
            "(status = 'blocked_downstream') OR (blocked_by IS NULL)",
            name="ck_failure_clusters_blocked_by",
        ),
        Index("ix_failure_clusters_project_seen", "project_id", desc("last_seen_at")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    failure_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    """Why these were grouped, in the terms that grouped them. Stored rather than
    recomputed: a reader has to be able to disagree with a cluster months later."""

    observation: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    route: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    representative_run_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    blocked_by: Mapped[str | None] = mapped_column(String(IDENTIFIER_LENGTH), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    members: Mapped[list["FailureClusterMemberModel"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan", lazy="selectin"
    )
    hypotheses: Mapped[list["ClusterHypothesisModel"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan", lazy="selectin"
    )


class FailureClusterMemberModel(Base):
    """Which failures a cluster is made of.

    A pair pointing at `criterion_results`, not a copy of it: the observation, the
    evidence refs and the model-derived flag already live there, and duplicating them
    would create a second version of the truth that can drift from the first.
    """

    __tablename__ = "failure_cluster_members"
    __table_args__ = (
        UniqueConstraint(
            "cluster_pk", "run_id", "criterion_id", name="uq_failure_cluster_members_identity"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_pk: Mapped[int] = mapped_column(
        Integer, ForeignKey("failure_clusters.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)

    cluster: Mapped[FailureClusterModel] = relationship(back_populates="members")


class ClusterHypothesisModel(Base):
    """A deep model's reading of a cluster. Separate table, on purpose (Phase 11).

    One row per cluster per analysis pass, keyed by the run boundary that triggered it,
    so a retried activity re-inserts nothing. Older rows are kept: how the explanation
    changed as a cluster grew is worth more than the latest guess alone.
    """

    __tablename__ = "cluster_hypotheses"
    __table_args__ = (
        UniqueConstraint("cluster_pk", "analyzed_run_id", name="uq_cluster_hypotheses_pass"),
        # A row here is an interpretation and can never claim otherwise.
        CheckConstraint("model_derived", name="ck_cluster_hypotheses_model_derived"),
        CheckConstraint(
            "confidence IN ('low', 'medium', 'high')", name="ck_cluster_hypotheses_confidence"
        ),
        CheckConstraint(
            "(failure IS NULL) OR (probable_cause = '')",
            name="ck_cluster_hypotheses_failure_has_no_cause",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_pk: Mapped[int] = mapped_column(
        Integer, ForeignKey("failure_clusters.id", ondelete="CASCADE"), nullable=False
    )
    analyzed_run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False
    )
    probable_cause: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommended_check: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    model_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failure: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Why no hypothesis was produced. Recorded rather than dropped: "the deep model
    was down" is the difference between a cluster nobody explained and one nobody
    asked about."""

    model_invocation_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cluster: Mapped[FailureClusterModel] = relationship(back_populates="hypotheses")


class ExploredStateModel(Base):
    """One state one exploring run reached (Phase 12).

    Per run, not per project: comparing this run's map against the previous one is what
    turns "we found a page" into "this page is new". A single accumulating table could
    say what exists but never what changed, and "what changed" is the whole point of a
    periodic regression.

    `affordance_keys` is the normalised set the signature was built from — stored so a
    delta can say *what* a page gained or lost, not merely that it differs. It is
    derived data with a stable derivation, which is why it can live in JSONB: the
    signature is the identity, and the keys are what the identity was computed from.
    """

    __tablename__ = "explored_states"
    __table_args__ = (
        UniqueConstraint("run_id", "signature", name="uq_explored_states_identity"),
        Index("ix_explored_states_project_route", "project_id", "route"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    signature: Mapped[str] = mapped_column(String(64), nullable=False)
    route: Mapped[str] = mapped_column(String(2000), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    affordance_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExplorationRunModel(Base):
    """What one exploring run spent, and whether its map is complete.

    Separate from the states because it answers a different question, and one the states
    cannot: a map of twelve states that ran out of actions and a map of twelve states
    that ran out of places to go look identical. Only the second can support the claim
    that a state missing next time was removed.
    """

    __tablename__ = "exploration_runs"
    __table_args__ = (
        CheckConstraint(
            "stop_reason IN ('goal_reached', 'frontier_exhausted', 'max_actions', "
            "'max_states', 'deadline')",
            name="ck_exploration_runs_stop_reason",
        ),
    )

    run_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stop_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actions_taken: Mapped[int] = mapped_column(Integer, nullable=False)
    states_discovered: Mapped[int] = mapped_column(Integer, nullable=False)
    max_depth_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    frontier_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    declined: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Controls the run was not allowed to take. Reported, because "mapped 12 states"
    and "mapped 12 states and left 4 buttons alone" are different findings."""

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
