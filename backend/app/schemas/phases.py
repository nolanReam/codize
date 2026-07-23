from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class TaskUpdateRequest(BaseModel):
    completed: bool


class AssignmentSelectionRequest(BaseModel):
    """The client chooses identity only; task content and ownership stay server-owned."""

    model_config = ConfigDict(extra="forbid")
    task_id: Annotated[str, Field(pattern=r"^(ai|human)-[1-9][0-9]*$")]
