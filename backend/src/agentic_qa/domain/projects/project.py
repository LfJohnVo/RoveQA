"""Project aggregate root (Projects bounded context)."""

from dataclasses import dataclass

from agentic_qa.domain.validation import MAX_NAME_LENGTH, require_identifier, require_text


@dataclass
class Project:
    project_id: str
    name: str

    def __post_init__(self) -> None:
        self.project_id = require_identifier(self.project_id, field="project_id")
        self.name = require_text(self.name, field="name", max_length=MAX_NAME_LENGTH)

    def rename(self, new_name: str) -> None:
        self.name = require_text(new_name, field="name", max_length=MAX_NAME_LENGTH)
