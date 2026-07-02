from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: int = Field(ge=1, le=5)
    answer: str
