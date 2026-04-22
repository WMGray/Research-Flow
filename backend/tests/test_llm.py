from __future__ import annotations

import argparse
import asyncio
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest
from agno.models.base import Model


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings, reset_settings
from app.core.llm_config import LLMFeatureConfig, LLMModelConfig
from app.services.llm.providers import BaseLLMProvider
from app.services.llm.registry import LLMRegistry, llm_registry
from app.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse


class DummyProvider(BaseLLMProvider):
    def build_model(self, feature: LLMFeatureConfig, model_entry: LLMModelConfig, request: LLMRequest) -> Model:
        raise NotImplementedError("DummyProvider.generate bypasses Agno model creation in tests")

    async def generate(
        self,
        feature_name: str,
        feature: LLMFeatureConfig,
        model_key: str,
        model_entry: LLMModelConfig,
        request: LLMRequest,
    ) -> LLMResponse:
        return LLMResponse(
            feature=feature_name,
            model_key=model_key,
            platform=self.platform_name,
            provider=self.platform.provider,
            model=model_entry.model_id,
            message=LLMMessage(role="assistant", content=request.messages[-1].content.upper()),
        )


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


STATUS_ICON = {"success": "🟢", "failure": "🔴", "warning": "🟡"}
RESULT_TEXT = {"success": "成功", "failure": "失败", "warning": "异常"}


@dataclass(frozen=True)
class ConnectivityResult:
    level: str
    platform: str
    model: str
    result: str
    detail: str
    reply: str | None = None


def get_visual_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F", "A") else 1
    return width


def visual_ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - get_visual_width(text))


def format_row(result: ConnectivityResult) -> str:
    return (
        f"| {visual_ljust(STATUS_ICON[result.level], 4)} "
        f"| {visual_ljust(result.platform[:14], 14)} "
        f"| {visual_ljust(result.model[:36], 36)} "
        f"| {visual_ljust(result.result, 8)} "
        f"| {result.detail}"
    )


async def _probe_model_connectivity(model_key: str, model_entry, timeout_seconds: float) -> ConnectivityResult:
    if not model_entry.enabled:
        return ConnectivityResult("warning", model_entry.platform, model_entry.model_id, RESULT_TEXT["warning"], "disabled")

    start = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_seconds):
            provider = llm_registry._get_provider(model_entry.platform)
            feature = LLMFeatureConfig(model_key=model_key, max_tokens=10, temperature=0)
            request = LLMRequest(messages=[LLMMessage(role="user", content="Reply with exactly OK.")])
            response = await provider.generate("connectivity_test", feature, model_key, model_entry, request)
            elapsed_ms = round((time.perf_counter() - start) * 1000)
            content = response.message.content.strip()
            if content:
                return ConnectivityResult("success", model_entry.platform, model_entry.model_id, RESULT_TEXT["success"], f"{elapsed_ms}ms", reply=content)
            return ConnectivityResult("warning", model_entry.platform, model_entry.model_id, RESULT_TEXT["warning"], "empty response")
    except asyncio.TimeoutError:
        return ConnectivityResult("failure", model_entry.platform, model_entry.model_id, RESULT_TEXT["failure"], "测试硬超时(30s)")
    except Exception as exc:  # noqa: BLE001
        return ConnectivityResult(
            "failure",
            model_entry.platform,
            model_entry.model_id,
            RESULT_TEXT["failure"],
            str(exc).split("\n")[0][:60],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test LLM connectivity using the app registry (Agno).")
    parser.add_argument("--platform", action="append", default=[], help="Only test specific platform names.")
    parser.add_argument("--model-key", action="append", default=[], help="Only test specific model keys.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled model entries.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Hard timeout per model in seconds.")
    return parser.parse_args()


async def run_connectivity_cli() -> int:
    args = parse_args()
    all_models = llm_registry.list_models(enabled_only=not args.include_disabled)
    selected_platforms = set(args.platform)
    selected_model_keys = set(args.model_key)

    test_tasks = []
    for model_key, model_entry in all_models.items():
        if selected_model_keys and model_key not in selected_model_keys:
            continue
        if selected_platforms and model_entry.platform not in selected_platforms:
            continue
        test_tasks.append(_probe_model_connectivity(model_key, model_entry, args.timeout))

    if not test_tasks:
        print("没有匹配到可测试的模型。")
        return 1

    print(f"开始测试 {len(test_tasks)} 个模型...")
    results = await asyncio.gather(*test_tasks)

    header = (
        f"| {visual_ljust('状态', 4)} "
        f"| {visual_ljust('平台', 14)} "
        f"| {visual_ljust('模型', 36)} "
        f"| {visual_ljust('结果', 8)} "
        f"| 耗时/原因"
    )
    sep = f"|{'-'*6}|{'-'*16}|{'-'*38}|{'-'*10}|{'-'*30}"

    print(sep)
    print(header)
    print(sep)
    for result in results:
        print(format_row(result))
    print(sep)

    return 0 if all(result.level == "success" for result in results) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run_connectivity_cli()))
    except KeyboardInterrupt:
        print("\n用户中断测试。")
        raise SystemExit(1)
