from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from agno.models.base import Model

from app.core.config import get_settings, reset_settings
from app.core.llm_config import LLMFeatureConfig, LLMModelConfig
from app.services.llm.providers import BaseLLMProvider
from app.services.llm.registry import LLMRegistry
from app.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse


class DummyProvider(BaseLLMProvider):
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        raise NotImplementedError("DummyProvider.generate bypasses Agno model creation in tests")

    async def generate(self, feature_name: str, feature: LLMFeatureConfig, model_key: str, model_entry: LLMModelConfig, request: LLMRequest) -> LLMResponse:
        return LLMResponse(feature=feature_name, model_key=model_key, platform=self.platform_name, provider=self.platform.provider, model=model_entry.model_id, message=LLMMessage(role="assistant", content=request.messages[-1].content.upper()))


def test_llm_registry_dispatches_default_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-registry"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm]",
                'default_feature = "default_chat"',
                "",
                "[llm.platforms.deepseek]",
                'provider_type = "openai_compatible"',
                'base_url = "https://api.deepseek.com/v1"',
                'api_key = "${DEEPSEEK_API_KEY}"',
                "",
                "[llm.models.chat_fast]",
                'platform = "deepseek"',
                'model = "deepseek-chat"',
                'purpose = "fast chat"',
                "temperature = 0.7",
                "max_tokens = 4096",
                "",
                "[llm.features.default_chat]",
                'model = "chat_fast"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    reset_settings()

    registry = LLMRegistry(provider_factories={"openai_compatible": DummyProvider})
    response = asyncio.run(registry.generate(LLMRequest(messages=[LLMMessage(role="user", content="hello")])))

    assert response.feature == "default_chat"
    assert response.model_key == "chat_fast"
    assert response.platform == "deepseek"
    assert response.provider == "openai_compatible"
    assert response.model == "deepseek-chat"
    assert response.message.content == "HELLO"


def test_llm_registry_auto_registers_platforms_from_toml(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-platform-sync-toml"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm.platforms.openrouter]",
                'provider_type = "openai_compatible"',
                'base_url = "https://openrouter.ai/api/v1"',
                'api_key = "${OPENROUTER_API_KEY}"',
                "",
                "[llm.models.router_chat]",
                'platform = "openrouter"',
                'model = "openai/gpt-4.1-mini"',
                "",
                "[llm.features.default_chat]",
                'model = "router_chat"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    reset_settings()

    registry = LLMRegistry(provider_factories={"openai_compatible": DummyProvider})
    providers = registry.sync_platforms()

    assert "openrouter" in registry.list_platforms()
    assert "openrouter" in providers


def test_llm_registry_auto_registers_platforms_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-platform-sync-env"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text("", encoding="utf-8")

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("LLM__DEFAULT_FEATURE", "env_chat")
    monkeypatch.setenv("LLM__PLATFORMS__ENV_PROXY__PROVIDER_TYPE", "openai_compatible")
    monkeypatch.setenv("LLM__PLATFORMS__ENV_PROXY__BASE_URL", "https://proxy.example/v1")
    monkeypatch.setenv("LLM__PLATFORMS__ENV_PROXY__API_KEY", "${ENV_PROXY_API_KEY}")
    monkeypatch.setenv("ENV_PROXY_API_KEY", "env-proxy-key")
    monkeypatch.setenv("LLM__MODELS__ENV_MODEL__PLATFORM", "env_proxy")
    monkeypatch.setenv("LLM__MODELS__ENV_MODEL__MODEL", "proxy-chat")
    monkeypatch.setenv("LLM__FEATURES__ENV_CHAT__MODEL", "env_model")
    reset_settings()

    registry = LLMRegistry(provider_factories={"openai_compatible": DummyProvider})
    response = asyncio.run(registry.generate(LLMRequest(feature="env_chat", messages=[LLMMessage(role="user", content="hi")])))

    assert "env_proxy" in registry.sync_platforms()
    assert response.platform == "env_proxy"
    assert response.provider == "openai_compatible"
    assert response.model == "proxy-chat"


def test_llm_platform_resolves_env_placeholder_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-platform-env"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm.platforms.openrouter]",
                'provider_type = "openai_compatible"',
                'base_url = "https://openrouter.ai/api/v1"',
                'api_key = "${OPENROUTER_API_KEY}"',
                "timeout = 90",
                "max_retries = 2",
                "",
                "[llm.platforms.openrouter.extra_headers]",
                'HTTP-Referer = "https://your-app.example.com"',
                'X-Title = "Research Flow"',
                "",
                "[llm.models.router_chat]",
                'platform = "openrouter"',
                'model = "openai/gpt-4.1-mini"',
                "",
                "[llm.features.default_chat]",
                'model = "router_chat"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    reset_settings()

    platform = get_settings().llm.platforms["openrouter"]
    client_kwargs = platform.client_kwargs()

    assert platform.provider == "openai_compatible"
    assert platform.resolve_api_key() == "test-openrouter-key"
    assert client_kwargs["base_url"] == "https://openrouter.ai/api/v1"
    assert client_kwargs["extra_headers"]["HTTP-Referer"] == "https://your-app.example.com"
    assert client_kwargs["extra_headers"]["X-Title"] == "Research Flow"


def test_llm_platform_accepts_legacy_provider_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-platform-provider-alias"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm.platforms.openai_proxy]",
                'provider = "openai"',
                "",
                "[llm.models.proxy_chat]",
                'platform = "openai_proxy"',
                'model = "gpt-4.1-mini"',
                "",
                "[llm.features.default_chat]",
                'model = "proxy_chat"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    reset_settings()

    platform = get_settings().llm.platforms["openai_proxy"]
    assert platform.provider == "openai_compatible"


def test_llm_platform_reads_anthropic_auth_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-platform-anthropic-auth"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm.platforms.anthropic_main]",
                'provider_type = "anthropic"',
                "",
                "[llm.models.claude_sonnet_main]",
                'platform = "anthropic_main"',
                'model = "claude-sonnet-4-5"',
                "",
                "[llm.features.default_chat]",
                'model = "claude_sonnet_main"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-auth-token")
    reset_settings()

    platform = get_settings().llm.platforms["anthropic_main"]
    assert platform.provider == "anthropic"
    assert platform.resolve_api_key() is None
    assert platform.resolve_auth_token() == "test-auth-token"
    assert platform.client_kwargs()["auth_token"] == "test-auth-token"


def test_llm_registry_lists_enabled_models(monkeypatch: pytest.MonkeyPatch) -> None:
    temp_dir = Path(".uv-cache") / "test-llm-model-library"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_file = temp_dir / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                "[llm.platforms.deepseek]",
                'provider_type = "openai_compatible"',
                "",
                "[llm.models.primary]",
                'platform = "deepseek"',
                'model = "deepseek-chat"',
                "",
                "[llm.models.shadow]",
                'platform = "deepseek"',
                'model = "deepseek-reasoner"',
                "enabled = false",
                "",
                "[llm.features.default_chat]",
                'model = "primary"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("RESEARCH_FLOW_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("RESEARCH_FLOW_ENV_FILE", "none")
    reset_settings()

    registry = LLMRegistry(provider_factories={"openai_compatible": DummyProvider})
    assert list(registry.list_models().keys()) == ["primary"]
    assert set(registry.list_models(enabled_only=False).keys()) == {"primary", "shadow"}
