from __future__ import annotations

from dataclasses import dataclass, field


class ConfigRepositoryError(RuntimeError):
    code = "CONFIG_REPOSITORY_ERROR"


class ConfigNotFoundError(ConfigRepositoryError):
    code = "CONFIG_NOT_FOUND"


class ConfigConflictError(ConfigRepositoryError):
    code = "CONFIG_CONFLICT"


@dataclass(frozen=True, slots=True)
class AgentProfileRecord:
    profile_key: str
    scene: str
    provider: str
    model_name: str
    temperature: float | None
    max_tokens: int | None
    enabled: bool
    updated_at: str


@dataclass(frozen=True, slots=True)
class SkillBindingRecord:
    skill_key: str
    scene: str
    agent_profile_key: str
    runtime_instruction_key: str
    toolset: list[str] = field(default_factory=list)
    enabled: bool = True
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class LLMProbeResultRecord:
    profile_key: str
    provider: str
    model_name: str
    connectivity_status: str
    ttft_ms: int | None
    checked_at: str
    error_message: str


@dataclass(frozen=True, slots=True)
class SkillCatalogRecord:
    skill_name: str
    description: str
    path: str
    has_runtime_instructions: bool
    has_agent_metadata: bool
