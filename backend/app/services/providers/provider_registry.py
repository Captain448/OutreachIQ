import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, NormalizedJob, NormalizedCompany
from app.services.providers.tavily_adapter import TavilyAdapter
from app.services.providers.exa_adapter import ExaAdapter
from app.services.providers.remotive_adapter import RemotiveAdapter
from app.services.providers.jsearch_adapter import JSearchAdapter
from app.services.providers.serpapi_adapter import SerpApiAdapter
from app.services.providers.adzuna_adapter import AdzunaAdapter
from app.services.providers.jooble_adapter import JoobleAdapter


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {
            "tavily": TavilyAdapter(),
            "exa": ExaAdapter(),
            "remotive": RemotiveAdapter(),
            "adzuna": AdzunaAdapter(),
            "jooble": JoobleAdapter(),
            "jsearch": JSearchAdapter(),
            "serpapi": SerpApiAdapter(),
        }
        # In-memory query cache to prevent repeat API calls & expenses: {cache_key: (timestamp, results)}
        self._jobs_cache: Dict[str, Tuple[float, List[NormalizedJob]]] = {}
        self._companies_cache: Dict[str, Tuple[float, List[NormalizedCompany]]] = {}

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name.lower())

    def get_all_providers(self) -> List[BaseProvider]:
        return list(self._providers.values())

    def get_configured_providers(self) -> List[BaseProvider]:
        return [p for p in self._providers.values() if p.is_configured()]

    def get_tier1_providers(self) -> List[BaseProvider]:
        """Returns configured Tier 1 providers ordered by DISCOVERY_TIER1_PROVIDERS config."""
        configured = self.get_configured_providers()
        ordered = []
        for name in settings.DISCOVERY_TIER1_PROVIDERS:
            for p in configured:
                if getattr(p, "provider_name", None) == name and p not in ordered:
                    ordered.append(p)
        for p in configured:
            tier_val = getattr(p, "tier", 1)
            if (tier_val == 1 or not isinstance(tier_val, int)) and p not in ordered and getattr(p, "provider_name", None) not in settings.DISCOVERY_TIER2_PROVIDERS:
                ordered.append(p)
        return ordered

    def get_tier2_providers(self) -> List[BaseProvider]:
        """Returns configured Tier 2 providers ordered by DISCOVERY_TIER2_PROVIDERS config."""
        configured = self.get_configured_providers()
        ordered = []
        for name in settings.DISCOVERY_TIER2_PROVIDERS:
            for p in configured:
                if getattr(p, "provider_name", None) == name and p not in ordered:
                    ordered.append(p)
        for p in configured:
            if getattr(p, "tier", None) == 2 and p not in ordered:
                ordered.append(p)
        return ordered

    def clear_cache(self) -> None:
        self._jobs_cache.clear()
        self._companies_cache.clear()

    def get_all_health_statuses(self) -> List[Dict[str, Any]]:
        return [p.get_health_status() for p in self._providers.values()]

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        raw = f"{prefix}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def search_jobs(
        self,
        provider_name: str,
        query: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 15
    ) -> List[NormalizedJob]:
        provider = self.get_provider(provider_name)
        if not provider or not provider.is_configured():
            return []

        cache_key = self._generate_cache_key("jobs", provider=provider_name, q=query, loc=location, r=remote_only)
        now = time.time()
        
        # Check cache
        if cache_key in self._jobs_cache:
            ts, cached_jobs = self._jobs_cache[cache_key]
            if now - ts < settings.DISCOVERY_CACHE_TTL_SECONDS:
                return cached_jobs

        results = await provider.search_jobs(query=query, location=location, remote_only=remote_only, limit=limit)
        self._jobs_cache[cache_key] = (now, results)
        return results

    async def search_companies(
        self,
        provider_name: str,
        skills: List[str],
        industries: List[str],
        roles: List[str],
        locations: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NormalizedCompany]:
        provider = self.get_provider(provider_name)
        if not provider or not provider.is_configured():
            return []

        cache_key = self._generate_cache_key(
            "companies",
            provider=provider_name,
            s=",".join(sorted(skills[:4])),
            i=",".join(sorted(industries[:2])),
            r=",".join(sorted(roles[:2])),
            loc=",".join(sorted(locations[:1])) if locations else "any"
        )
        now = time.time()

        if cache_key in self._companies_cache:
            ts, cached_comp = self._companies_cache[cache_key]
            if now - ts < settings.DISCOVERY_CACHE_TTL_SECONDS:
                return cached_comp

        results = await provider.search_companies(
            skills=skills,
            industries=industries,
            roles=roles,
            locations=locations,
            limit=limit
        )
        self._companies_cache[cache_key] = (now, results)
        return results


provider_registry = ProviderRegistry()
