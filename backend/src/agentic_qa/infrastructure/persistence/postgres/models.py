"""SQLAlchemy models. These types never leave infrastructure.

Tables follow docs/11-data-and-artifacts.md and are introduced phase by phase, not
in one mega migration.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
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
    )

    run_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("projects.project_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[RunStatus] = mapped_column(_string_enum(RunStatus, "run_status"), nullable=False)
    verdict: Mapped[Verdict | None] = mapped_column(
        _string_enum(Verdict, "run_verdict"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
