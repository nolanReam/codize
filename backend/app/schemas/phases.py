from pydantic import BaseModel


class TaskUpdateRequest(BaseModel):
    completed: bool
