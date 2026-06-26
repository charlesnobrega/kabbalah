"""Provider routing gateway for Kabbalah v2."""

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set


@dataclass(frozen=True)
class ProviderCandidate:
    name: str
    cost_per_1k_tokens: float
    capabilities: Set[str] = field(default_factory=set)
    available: bool = True
    max_risk: float = 1.0


class LLMGateway:
    """Select the cheapest available provider that satisfies requirements."""

    def __init__(self, providers: Optional[Iterable[ProviderCandidate]] = None):
        self.providers: List[ProviderCandidate] = list(providers or [])

    def registrar_provider(self, provider: ProviderCandidate) -> None:
        self.providers.append(provider)

    def selecionar_provider(
        self,
        *,
        required_capabilities: Optional[Set[str]] = None,
        risk_score: float = 0.0,
    ) -> ProviderCandidate:
        required = required_capabilities or set()
        candidates = [
            provider
            for provider in self.providers
            if provider.available
            and required.issubset(provider.capabilities)
            and risk_score <= provider.max_risk
        ]
        if not candidates:
            raise ValueError("No suitable provider available")
        return sorted(candidates, key=lambda provider: provider.cost_per_1k_tokens)[0]
