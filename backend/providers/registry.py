"""Typed provider registry; business services resolve providers by capability."""
from backend.providers.base import Provider

class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, dict[str, Provider]] = {}
    def register(self, provider_type: str, provider: Provider) -> None:
        bucket = self._providers.setdefault(provider_type, {})
        if provider.provider_name in bucket:
            raise ValueError(f"{provider_type} provider {provider.provider_name} already registered")
        bucket[provider.provider_name] = provider
    def get(self, provider_type: str, provider_name: str) -> Provider:
        try: return self._providers[provider_type][provider_name]
        except KeyError as exc: raise LookupError(f"No {provider_type} provider named {provider_name}") from exc
    def capabilities(self, provider_type: str, provider_name: str) -> dict: return self.get(provider_type, provider_name).get_capabilities()

def build_demo_registry() -> ProviderRegistry:
    from backend.providers.telephony.mock import MockTelephonyProvider
    from backend.providers.stt.mock import MockSTTProvider
    from backend.providers.tts.mock import MockTTSProvider
    from backend.providers.llm.mock import MockLLMProvider
    from backend.providers.phone_number.mock import MockPhoneNumberProvider
    registry = ProviderRegistry()
    for kind, provider in (("telephony", MockTelephonyProvider()), ("stt", MockSTTProvider()), ("tts", MockTTSProvider()), ("llm", MockLLMProvider()), ("phone_number", MockPhoneNumberProvider())): registry.register(kind, provider)
    return registry
