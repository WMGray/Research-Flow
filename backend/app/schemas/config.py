from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentProfileResponse(BaseModel):
    profile_key: str
    scene: str
    provider: str
    model_name: str
    temperature: float | None = None
    max_tokens: int | None = None
    enabled: bool
    updated_at: str


class AgentProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None, min_length=1)
    model_name: str | None = Field(default=None, min_length=1)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "AgentProfileUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class SkillCatalogResponse(BaseModel):
    skill_name: str
    description: str
    path: str
    has_runtime_instructions: bool
    has_agent_metadata: bool


class SkillBindingResponse(BaseModel):
    skill_key: str
    scene: str
    agent_profile_key: str
    runtime_instruction_key: str = ""
    toolset: list[str] = Field(default_factory=list)
    enabled: bool
    updated_at: str


class SkillBindingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: str | None = Field(default=None, min_length=1)
    agent_profile_key: str | None = Field(default=None, min_length=1)
    runtime_instruction_key: str | None = None
    toolset: list[str] | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "SkillBindingUpdateRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided.")
        return self


class LLMStatusResponse(BaseModel):
    profile_key: str
    provider: str
    model_name: str
    connectivity_status: str
    ttft_ms: int | None = None
    checked_at: str
    error_message: str = ""
