"""Environment: a deployment of the target application a run executes against."""

from dataclasses import dataclass

from agentic_qa.domain.validation import MAX_NAME_LENGTH, require_identifier, require_text


@dataclass
class Environment:
    environment_id: str
    project_id: str
    name: str
    default_run_policy_id: str | None = None
    """Used when a run does not name a policy of its own (docs/12 resolution order)."""

    def __post_init__(self) -> None:
        self.environment_id = require_identifier(self.environment_id, field="environment_id")
        self.project_id = require_identifier(self.project_id, field="project_id")
        self.name = require_text(self.name, field="name", max_length=MAX_NAME_LENGTH)
        if self.default_run_policy_id is not None:
            self.default_run_policy_id = require_identifier(
                self.default_run_policy_id, field="default_run_policy_id"
            )
