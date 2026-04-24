from __future__ import annotations

from collections.abc import Callable

from core.config import Settings, get_settings
from core.llm_config import LLMFeatureConfig, LLMModelConfig, LLMPlatformConfig
from core.services.llm.providers import BaseLLMProvider, PROVIDER_FACTORIES
from core.services.llm.schemas import LLMRequest, LLMResponse


ProviderFactory = type[BaseLLMProvider]


class LLMRegistry:
    """注册中心：从配置中自动同步平台，再按功能路由到模型库和协议适配器。"""

    def __init__(self, settings_loader: Callable[[], Settings] = get_settings, provider_factories: dict[str, ProviderFactory] | None = None) -> None:
        self.settings_loader = settings_loader
        self.provider_factories = provider_factories or PROVIDER_FACTORIES
        self._providers: dict[str, BaseLLMProvider] = {}

    def reset(self) -> None:
        self._providers.clear()

    def list_platforms(self) -> dict[str, LLMPlatformConfig]:
        return self.settings_loader().llm.platforms

    def list_models(self, enabled_only: bool = True) -> dict[str, LLMModelConfig]:
        models = self.settings_loader().llm.models
        return {model_key: model for model_key, model in models.items() if model.enabled or not enabled_only}

    def list_features(self) -> dict[str, LLMFeatureConfig]:
        return self.settings_loader().llm.features

    def _build_provider(self, platform_name: str, platform: LLMPlatformConfig) -> BaseLLMProvider:
        if platform.provider not in self.provider_factories:
            raise KeyError(f"Unsupported llm provider: {platform.provider}")
        return self.provider_factories[platform.provider](platform_name, platform)

    def sync_platforms(self) -> dict[str, BaseLLMProvider]:
        """把当前 settings 里声明的平台自动注册到 provider 缓存中。"""
        for platform_name, platform in self.settings_loader().llm.platforms.items():
            if platform_name not in self._providers:
                self._providers[platform_name] = self._build_provider(platform_name, platform)
        return self._providers

    def _resolve_feature(self, feature_name: str | None) -> tuple[str, LLMFeatureConfig]:
        llm_settings = self.settings_loader().llm
        resolved_feature = feature_name or llm_settings.default_feature
        if resolved_feature is None:
            raise ValueError("llm.default_feature is not configured and request.feature is empty")
        if resolved_feature not in llm_settings.features:
            raise KeyError(f"Unknown llm feature: {resolved_feature}")
        return resolved_feature, llm_settings.features[resolved_feature]

    def _resolve_model(self, model_key: str) -> LLMModelConfig:
        llm_settings = self.settings_loader().llm
        if model_key not in llm_settings.models:
            raise KeyError(f"Unknown llm model: {model_key}")
        model_entry = llm_settings.models[model_key]
        if not model_entry.enabled:
            raise ValueError(f"llm model '{model_key}' is disabled")
        return model_entry

    def _get_provider(self, platform_name: str) -> BaseLLMProvider:
        self.sync_platforms()
        if platform_name not in self._providers:
            raise KeyError(f"Unknown llm platform: {platform_name}")
        return self._providers[platform_name]

    async def generate(self, request: LLMRequest) -> LLMResponse:
        feature_name, feature = self._resolve_feature(request.feature)
        model_key = feature.model_key
        model_entry = self._resolve_model(model_key)
        provider = self._get_provider(model_entry.platform)
        return await provider.generate(feature_name, feature, model_key, model_entry, request)


llm_registry = LLMRegistry()
