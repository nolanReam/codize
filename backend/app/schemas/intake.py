from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: int = Field(ge=1, le=5)
    answer: str


EntrySituation = Literal["starting_fresh", "already_building", "stuck"]
CodingConfidence = Literal["new_to_code", "know_basics", "comfortable"]
AiChangeState = Literal["yes", "not_yet", "unsure"]
RecommendedStart = Literal["prompt_builder", "implementation_import", "quick_start"]
GuidanceDepth = Literal["more", "standard", "minimal"]


class EntryProfileUpdateRequest(BaseModel):
    """Student-owned orientation choices only.

    Recommendation, guidance depth, recovery emphasis, completion, and every
    workflow lifecycle field are deliberately absent and therefore rejected.
    """

    model_config = ConfigDict(extra="forbid")

    current_situation: EntrySituation | None = None
    coding_confidence: CodingConfidence | None = None
    ai_changed_files: AiChangeState | None = None

    @model_validator(mode="after")
    def _at_least_one_choice(self) -> "EntryProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("at least one entry choice is required")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("entry choices cannot be null")
        if (
            "current_situation" in self.model_fields_set
            and self.current_situation != "already_building"
            and "ai_changed_files" in self.model_fields_set
            and self.ai_changed_files is not None
        ):
            raise ValueError(
                "ai_changed_files applies only when current_situation is already_building"
            )
        return self


class EntryProfileView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    current_situation: EntrySituation | None
    coding_confidence: CodingConfidence | None
    ai_changed_files: AiChangeState | None
    completed: bool
    recommended_start: RecommendedStart | None
    guidance_depth: GuidanceDepth
    recovery_emphasis: bool
    updated_at: str
