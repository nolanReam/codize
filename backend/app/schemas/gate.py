"""Gate request bodies. Input validation at the boundary: student text is
bounded and non-blank; everything else about it is treated as answer content,
never as instructions (prompt files enforce that downstream)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _NonBlank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _strip_and_require_content(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be blank")
        return value


class AnchorRequest(_NonBlank):
    anchor_statement: str = Field(min_length=1, max_length=2000)


class AnswerRequest(_NonBlank):
    answer: str = Field(min_length=1, max_length=8000)
