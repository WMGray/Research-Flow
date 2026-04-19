from __future__ import annotations

import os
import re
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


# platform 只描述“怎么连”，models 描述“模型库里有哪些模型”，features 描述“哪个功能用哪个模型”。
# 这里的 provider_type 表示协议适配器，不表示具体服务商；不同中转站只要兼容 OpenAI 协议，都应写成 openai_compatible。
LLMProviderType = Literal["openai_compatible", "openai", "anthropic", "dashscope", "deepseek"]

PROVIDER_TYPE_CANONICAL: dict[LLMProviderType, str] = {
    "openai_compatible": "openai_compatible",
    "openai": "openai_compatible",
    "deepseek": "openai_compatible",
    "anthropic": "anthropic",
    "dashscope": "dashscope",
}

API_KEY_ENV_FALLBACKS: dict[LLMProviderType, tuple[str, ...]] = {
    "openai_compatible": ("OPENAI_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "dashscope": ("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
}

AUTH_TOKEN_ENV_FALLBACKS: dict[LLMProviderType, tuple[str, ...]] = {
    "openai_compatible": (),
    "openai": (),
    "anthropic": ("ANTHROPIC_AUTH_TOKEN",),
    "dashscope": (),
    "deepseek": (),
}

BASE_URL_ENV_FALLBACKS: dict[LLMProviderType, tuple[str, ...]] = {
    "openai_compatible": ("OPENAI_BASE_URL",),
    "openai": ("OPENAI_BASE_URL",),
    "anthropic": (),
    "dashscope": ("DASHSCOPE_BASE_URL", "QWEN_BASE_URL"),
    "deepseek": ("DEEPSEEK_BASE_URL",),
}

ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return None


def _expand_env_placeholder(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    match = ENV_PLACEHOLDER_PATTERN.match(value)
    return os.getenv(match.group(1)) if match else value


def _resolved_value(explicit: str | None, *env_names: str) -> str | None:
    resolved_explicit = _expand_env_placeholder(explicit)
    return resolved_explicit or _first_env(*env_names)


class LLMPlatformConfig(BaseModel):
    """平台级配置：保存协议类型、base_url、api_key、header 等连接参数。"""

    model_config = ConfigDict(populate_by_name=True)

    provider_type: LLMProviderType = Field(validation_alias=AliasChoices("provider_type", "provider", "protocol"))
    api_key: str | None = None
    auth_token: str | None = None
    base_url: str | None = None
    organization: str | None = None
    timeout: float | None = None
    max_retries: int | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)

    @property
    def provider(self) -> str:
        return PROVIDER_TYPE_CANONICAL[self.provider_type]

    def resolve_api_key(self) -> str | None:
        return _resolved_value(self.api_key, *API_KEY_ENV_FALLBACKS[self.provider_type])

    def resolve_base_url(self) -> str | None:
        return _resolved_value(self.base_url, *BASE_URL_ENV_FALLBACKS[self.provider_type])

    def resolve_auth_token(self) -> str | None:
        return _resolved_value(self.auth_token, *AUTH_TOKEN_ENV_FALLBACKS[self.provider_type])

    def resolve_extra_headers(self) -> dict[str, str]:
        return {key: value for key, raw in self.extra_headers.items() if (value := _expand_env_placeholder(raw))}

    def client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"api_key": self.resolve_api_key(), "base_url": self.resolve_base_url(), "timeout": self.timeout, "max_retries": self.max_retries}
        if self.provider == "openai_compatible":
            kwargs["extra_headers"] = self.resolve_extra_headers()
            if self.organization is not None:
                kwargs["organization"] = _expand_env_placeholder(self.organization)
        if self.provider == "anthropic":
            kwargs["auth_token"] = self.resolve_auth_token()
            kwargs["default_headers"] = self.resolve_extra_headers()
        return {key: value for key, value in kwargs.items() if value not in (None, {})}


class LLMModelConfig(BaseModel):
    """模型库条目：定义模型本身、默认参数和能力标签。"""

    model_config = ConfigDict(populate_by_name=True)

    platform: str
    model_id: str = Field(validation_alias=AliasChoices("model_id", "model"))
    enabled: bool = True
    purpose: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    reasoning_effort: str | None = None
    supports_vision: bool | None = None
    supports_tools: bool | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LLMFeatureConfig(BaseModel):
    """功能级配置：从模型库中选择模型，并可按业务场景覆盖默认参数。"""

    model_config = ConfigDict(populate_by_name=True)

    model_key: str = Field(validation_alias=AliasChoices("model_key", "model"))
    system_prompt: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    reasoning_effort: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """LLM 总配置：平台、模型库、功能路由三层分离。"""

    model_config = ConfigDict(populate_by_name=True)

    default_feature: str | None = Field(default=None, validation_alias=AliasChoices("default_feature", "default_alias"))
    platforms: dict[str, LLMPlatformConfig] = Field(default_factory=dict)
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)
    features: dict[str, LLMFeatureConfig] = Field(default_factory=dict, validation_alias=AliasChoices("features", "aliases"))

    @model_validator(mode="after")
    def validate_references(self) -> "LLMConfig":
        # 启动时一次性校验引用关系，避免到请求阶段才发现配置写错。
        if self.default_feature is not None and self.default_feature not in self.features:
            raise ValueError(f"default_feature '{self.default_feature}' is not defined in llm.features")

        for model_key, model in self.models.items():
            if model.platform not in self.platforms:
                raise ValueError(f"llm.models.{model_key}.platform '{model.platform}' is not defined in llm.platforms")

        for feature_name, feature in self.features.items():
            if feature.model_key not in self.models:
                raise ValueError(f"llm.features.{feature_name}.model '{feature.model_key}' is not defined in llm.models")

        return self
