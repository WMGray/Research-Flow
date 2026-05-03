from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from app.api.papers import envelope
from app.schemas.config import (
    AgentProfileResponse,
    AgentProfileUpdateRequest,
    LLMStatusResponse,
    SkillBindingResponse,
    SkillBindingUpdateRequest,
    SkillCatalogResponse,
)
from app.schemas.papers import APIEnvelope
from core.services.system_config import (
    ConfigConflictError,
    ConfigNotFoundError,
    SystemConfigRepository,
)


router = APIRouter(prefix="/api/v1/config", tags=["config"])


def get_config_repository() -> SystemConfigRepository:
    return SystemConfigRepository()


def raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ConfigNotFoundError):
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, ConfigConflictError):
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": str(exc)},
        )
    raise exc


@router.get("/agents", response_model=APIEnvelope)
def list_agents(
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    return envelope(
        [
            AgentProfileResponse.model_validate(asdict(record))
            for record in repository.list_agents()
        ]
    )


@router.get("/agents/{profile_key}", response_model=APIEnvelope)
def get_agent(
    profile_key: str,
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    try:
        return envelope(
            AgentProfileResponse.model_validate(
                asdict(repository.get_agent(profile_key))
            )
        )
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put("/agents/{profile_key}", response_model=APIEnvelope)
def update_agent(
    profile_key: str,
    request: AgentProfileUpdateRequest,
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    try:
        record = repository.update_agent(
            profile_key,
            request.model_dump(exclude_unset=True),
        )
        return envelope(AgentProfileResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/llms/status", response_model=APIEnvelope)
def list_llm_status(
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    return envelope(
        [
            LLMStatusResponse.model_validate(asdict(record))
            for record in repository.list_llm_status()
        ]
    )


@router.get("/skills/catalog", response_model=APIEnvelope)
def list_skill_catalog(
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    return envelope(
        [
            SkillCatalogResponse.model_validate(asdict(record))
            for record in repository.list_skill_catalog()
        ]
    )


@router.get("/skills/catalog/{skill_name}", response_model=APIEnvelope)
def get_skill_catalog_item(
    skill_name: str,
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    try:
        record = repository.get_skill_catalog_item(skill_name)
        return envelope(SkillCatalogResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.get("/skills", response_model=APIEnvelope)
def list_skill_bindings(
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    return envelope(
        [
            SkillBindingResponse.model_validate(asdict(record))
            for record in repository.list_skill_bindings()
        ]
    )


@router.get("/skills/{skill_key}", response_model=APIEnvelope)
def get_skill_binding(
    skill_key: str,
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    try:
        record = repository.get_skill_binding(skill_key)
        return envelope(SkillBindingResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise


@router.put("/skills/{skill_key}", response_model=APIEnvelope)
def update_skill_binding(
    skill_key: str,
    request: SkillBindingUpdateRequest,
    repository: SystemConfigRepository = Depends(get_config_repository),
) -> APIEnvelope:
    try:
        record = repository.update_skill_binding(
            skill_key,
            request.model_dump(exclude_unset=True),
        )
        return envelope(SkillBindingResponse.model_validate(asdict(record)))
    except Exception as exc:  # pragma: no cover - centralized mapping
        raise_http_error(exc)
        raise
