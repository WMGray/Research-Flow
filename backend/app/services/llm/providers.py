from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agno.models.base import Model
from agno.models.message import Message as AgnoMessage
from agno.models.response import ModelResponse as AgnoModelResponse

from app.core.llm_config import LLMFeatureConfig, LLMModelConfig, LLMPlatformConfig
from app.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse, LLMUsage


class BaseLLMProvider(ABC):
    """Provider 适配层：负责把功能配置和模型库条目转换成 Agno 调用。"""

    def __init__(self, platform_name: str, platform: LLMPlatformConfig) -> None:
        self.platform_name = platform_name
        self.platform = platform

    async def generate(self, feature_name: str, feature: LLMFeatureConfig, model_key: str, model_entry: LLMModelConfig, request: LLMRequest) -> LLMResponse:
        model = self.build_model(feature, model_entry, request)
        messages = self.build_messages(feature, request.messages)
        model_response = await model.aresponse(messages=messages)
        return self.build_response(feature_name, model_key, model_entry, model_response)

    @abstractmethod
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        """按功能配置和模型库条目构造 Agno model。"""

    def build_messages(self, feature: LLMFeatureConfig, messages: list[LLMMessage]) -> list[AgnoMessage]:
        agno_messages: list[AgnoMessage] = []
        if feature.system_prompt:
            agno_messages.append(AgnoMessage(role="system", content=feature.system_prompt))
        agno_messages.extend(self.to_agno_message(message) for message in messages)
        return agno_messages

    def to_agno_message(self, message: LLMMessage) -> AgnoMessage:
        return AgnoMessage(role=message.role, content=message.content, name=message.name, tool_call_id=message.tool_call_id, tool_calls=message.tool_calls or None)

    def build_usage(self, model_response: AgnoModelResponse) -> LLMUsage | None:
        usage = model_response.response_usage
        if usage is None:
            return None
        return LLMUsage(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, total_tokens=usage.total_tokens, reasoning_tokens=usage.reasoning_tokens, cache_read_tokens=usage.cache_read_tokens, cache_write_tokens=usage.cache_write_tokens)

    def build_response(self, feature_name: str, model_key: str, model_entry: LLMModelConfig, model_response: AgnoModelResponse) -> LLMResponse:
        content = model_response.content if model_response.content is not None else model_response.parsed
        return LLMResponse(feature=feature_name, model_key=model_key, platform=self.platform_name, provider=self.platform.provider, model=model_entry.model_id, message=LLMMessage(role="assistant", content="" if content is None else str(content), tool_calls=self.normalize_tool_calls(model_response.tool_calls)), usage=self.build_usage(model_response), provider_data=model_response.provider_data, raw_content=model_response.content)

    def normalize_tool_calls(self, tool_calls: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for tool_call in tool_calls or []:
            if isinstance(tool_call, dict):
                normalized.append(tool_call)
                continue
            if hasattr(tool_call, "model_dump"):
                normalized.append(tool_call.model_dump(mode="json"))
                continue
            normalized.append({"value": str(tool_call)})
        return normalized

    def _pick_override(self, request_value: Any, feature_value: Any, model_value: Any) -> Any:
        return request_value if request_value is not None else feature_value if feature_value is not None else model_value

    def merged_model_kwargs(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> dict[str, Any]:
        kwargs = self.platform.client_kwargs()
        kwargs.update({"id": model_entry.model_id, "temperature": self._pick_override(request.temperature, feature.temperature, model_entry.temperature), "top_p": self._pick_override(request.top_p, feature.top_p, model_entry.top_p), "max_tokens": self._pick_override(request.max_tokens, feature.max_tokens, model_entry.max_tokens)})

        max_completion_tokens = self._pick_override(request.max_completion_tokens, feature.max_completion_tokens, model_entry.max_completion_tokens)
        if max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = max_completion_tokens

        reasoning_effort = self._pick_override(request.reasoning_effort, feature.reasoning_effort, model_entry.reasoning_effort)
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        kwargs.update(model_entry.extra)
        kwargs.update(feature.extra)
        kwargs.update(request.extra)
        return {key: value for key, value in kwargs.items() if value is not None}


class OpenAICompatibleProvider(BaseLLMProvider):
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        from agno.models.openai import OpenAIChat

        return OpenAIChat(**self.merged_model_kwargs(feature, model_entry, request))


class AnthropicProvider(BaseLLMProvider):
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        from agno.models.anthropic import Claude

        # Anthropic 不吃 OpenAI 风格的部分字段，这里在适配层裁掉。
        kwargs = self.merged_model_kwargs(feature, model_entry, request)
        kwargs.pop("max_completion_tokens", None)
        kwargs.pop("reasoning_effort", None)
        kwargs.pop("organization", None)
        kwargs.pop("base_url", None)
        kwargs.pop("max_retries", None)
        kwargs.pop("extra_headers", None)
        return Claude(**kwargs)


class DashScopeProvider(BaseLLMProvider):
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        from agno.models.dashscope import DashScope

        kwargs = self.merged_model_kwargs(feature, model_entry, request)
        kwargs.pop("organization", None)
        return DashScope(**kwargs)


# 这里的 key 表示协议适配器类型，不表示具体服务商。
PROVIDER_FACTORIES = {"openai_compatible": OpenAICompatibleProvider, "anthropic": AnthropicProvider, "dashscope": DashScopeProvider}
