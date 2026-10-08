"""Internal provider selection with health, capability, language, and fallback checks."""
from dataclasses import dataclass
from typing import Any, Optional
from backend.providers.registry import ProviderRegistry

@dataclass(frozen=True)
class ResolvedProvider:
    provider: Any
    provider_resource_id: str | None
    provider_type: str

class ProviderRouter:
    def __init__(self, registry: ProviderRegistry, health: dict[tuple[str,str], bool] | None=None, failover_log: list[dict] | None=None, db=None):
        self.registry=registry; self.health=health or {}; self.failover_log=failover_log if failover_log is not None else []; self.db=db
    def _resolve(self, provider_type: str, name: str, resource_id: str | None, language: str | None) -> ResolvedProvider:
        if self.health.get((provider_type,name), True) is False: raise ValueError(f'Provider {name} is unhealthy')
        provider=self.registry.get(provider_type,name)
        caps=provider.get_capabilities(); languages=caps.get('languages')
        if language and languages and language not in languages: raise ValueError(f'Provider {name} does not support {language}')
        return ResolvedProvider(provider, resource_id, provider_type)
    def resolve(self, route: dict) -> ResolvedProvider:
        kind=route['provider_type']; language=route.get('language')
        try: return self._resolve(kind,route['provider'],route.get('provider_resource_id'),language)
        except (LookupError, ValueError) as primary_error:
            fallback=route.get('fallback_provider')
            if not fallback: raise primary_error
            resolved=self._resolve(kind,fallback,route.get('fallback_resource_id'),language)
            self.failover_log.append({'provider_type':kind,'from_provider':route['provider'],'to_provider':fallback,'reason':str(primary_error)})
            return resolved

    async def resolve_and_record(self, route: dict) -> ResolvedProvider:
        """Resolve a route and durably retain any failover event for operations review."""
        before=len(self.failover_log)
        resolved=self.resolve(route)
        if self.db is not None and len(self.failover_log) > before:
            from backend.models.base import new_id, utcnow
            event={"_id":new_id(), **self.failover_log[-1], "created_at":utcnow()}
            await self.db['provider_failover_events'].insert_one(event)
        return resolved
