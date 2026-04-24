from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field


LLMRole = Literal["system", "user", "assistant", "tool"]


class LLMMessage(BaseModel):
    """统一消息结构，屏蔽不同 provider 的字段差异。"""

    role: LLMRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class LLMRequest(BaseModel):
    """统一请求结构；`feature` 是业务功能名，也兼容旧的 `alias` 入参。"""

    feature: str | None = Field(default=None, validation_alias=AliasChoices("feature", "alias"))
    messages: list[LLMMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    reasoning_effort: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    """统一 token 统计结构，方便后续计费和日志记录。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class LLMResponse(BaseModel):
    """统一响应结构，返回功能路由、模型库命中结果和标准化消息。"""

    feature: str
    model_key: str
    platform: str
    provider: str
    model: str
    message: LLMMessage
    usage: LLMUsage | None = None
    provider_data: dict[str, Any] | None = None
    raw_content: Any | None = None
