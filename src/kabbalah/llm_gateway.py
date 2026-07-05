"""Canonical provider routing gateway for Kabbalah."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Protocol, Set

logger = logging.getLogger(__name__)


class ProviderFactoryProtocol(Protocol):
    """Minimal factory protocol used by the gateway."""

    def create_provider(self, provider_name: str, **kwargs: Any) -> Any:
        """Create a provider by name."""


@dataclass(frozen=True)
class ProviderCandidate:
    """Legacy candidate shape kept for backwards compatibility."""

    name: str
    cost_per_1k_tokens: float
    capabilities: Set[str] = field(default_factory=set)
    available: bool = True
    max_risk: float = 1.0


@dataclass(frozen=True)
class ModelProfile:
    """Capability and cost metadata for one selectable model/provider entry."""

    name: str
    provider_name: str
    model: str
    roles: Set[str]
    capabilities: Set[str]
    context_window: int
    input_cost_per_1m_tokens: float
    output_cost_per_1m_tokens: float
    license_type: str
    location: str
    tier: str
    backend: Optional[str] = None
    quant: Optional[str] = None
    min_vram_full: Optional[int] = None
    min_vram_offload: Optional[int] = None
    max_context_no_perfil: Optional[int] = None
    tokens_s_medido: Optional[float] = None
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    available: bool = True

    @property
    def total_cost_per_1m_tokens(self) -> float:
        """Return input+output cost for simple budget ordering/filtering."""
        return self.input_cost_per_1m_tokens + self.output_cost_per_1m_tokens

    def provider_kwargs(self) -> dict[str, Any]:
        """Build provider construction kwargs without exposing secret values."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "base_url": self.base_url,
        }
        if self.input_cost_per_1m_tokens:
            kwargs["input_cost_per_1m_tokens"] = self.input_cost_per_1m_tokens
        if self.output_cost_per_1m_tokens:
            kwargs["output_cost_per_1m_tokens"] = self.output_cost_per_1m_tokens
        if self.api_key_env:
            kwargs["api_key"] = os.getenv(self.api_key_env)
            kwargs["api_key_env"] = self.api_key_env
        return kwargs


@dataclass(frozen=True)
class ProviderSelection:
    """Result of a canonical gateway selection."""

    profile: ModelProfile
    provider: Any


class CapabilityRegistry:
    """In-memory registry of selectable model capability profiles."""

    def __init__(self, profiles: Optional[Iterable[ModelProfile]] = None):
        self._profiles: list[ModelProfile] = []
        for profile in profiles or []:
            self.register(profile)

    def register(self, profile: ModelProfile) -> None:
        """Register a model profile."""
        self._profiles.append(profile)

    def list_profiles(self) -> list[ModelProfile]:
        """Return all registered profiles."""
        return list(self._profiles)

    @classmethod
    def default(cls) -> "CapabilityRegistry":
        """Build the default registry, excluding cloud entries without keys."""
        profiles = [
            ModelProfile(
                name="ollama-local-default",
                provider_name="ollama_local",
                model=os.getenv("KABBALAH_OLLAMA_MODEL", "llama3.1"),
                roles={"Leaf_Builder", "Leaf_Verifier", "Domain_Coordinator"},
                capabilities={"chat", "code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.0,
                output_cost_per_1m_tokens=0.0,
                license_type="open",
                location="local",
                tier="local",
                backend="cpu",
                api_key_env=None,
                base_url="http://localhost:11434/v1",
            ),
            ModelProfile(
                name="openrouter-default",
                provider_name="openrouter",
                model=os.getenv("KABBALAH_OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                roles={"Root_Orchestrator", "Domain_Coordinator", "Leaf_Builder", "Leaf_Verifier"},
                capabilities={"chat", "code", "reasoning"},
                context_window=128000,
                input_cost_per_1m_tokens=0.15,
                output_cost_per_1m_tokens=0.60,
                license_type="agregador",
                location="cloud",
                tier="agregador",
                api_key_env="OPENROUTER_API_KEY",
                base_url="https://openrouter.ai/api/v1",
            ),
            ModelProfile(
                name="groq-fast-default",
                provider_name="groq_compatible",
                model=os.getenv("KABBALAH_GROQ_MODEL", "llama-3.1-8b-instant"),
                roles={"Leaf_Builder", "Leaf_Verifier"},
                capabilities={"chat", "code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.05,
                output_cost_per_1m_tokens=0.08,
                license_type="agregador",
                location="cloud",
                tier="fast",
                api_key_env="GROQ_API_KEY",
                base_url="https://api.groq.com/openai/v1",
            ),
            ModelProfile(
                name="cerebras-fast-default",
                provider_name="cerebras",
                model=os.getenv("KABBALAH_CEREBRAS_MODEL", "gpt-oss-120b"),
                roles={"Leaf_Builder", "Leaf_Verifier"},
                capabilities={"chat", "code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.10,
                output_cost_per_1m_tokens=0.10,
                license_type="agregador",
                location="cloud",
                tier="fast",
                api_key_env="CEREBRAS_API_KEY",
                base_url="https://api.cerebras.ai/v1",
            ),
            ModelProfile(
                name="sambanova-fast-default",
                provider_name="sambanova",
                model=os.getenv("KABBALAH_SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct"),
                roles={"Leaf_Builder", "Leaf_Verifier"},
                capabilities={"chat", "code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.10,
                output_cost_per_1m_tokens=0.10,
                license_type="agregador",
                location="cloud",
                tier="fast",
                api_key_env="SAMBANOVA_API_KEY",
                base_url="https://api.sambanova.ai/v1",
            ),
            ModelProfile(
                name="openai-premium-default",
                provider_name="openai",
                model=os.getenv("KABBALAH_OPENAI_MODEL", "gpt-4o"),
                roles={"Root_Orchestrator", "Domain_Coordinator"},
                capabilities={"chat", "reasoning"},
                context_window=128000,
                input_cost_per_1m_tokens=2.5,
                output_cost_per_1m_tokens=10.0,
                license_type="paga",
                location="cloud",
                tier="premium",
                api_key_env="OPENAI_API_KEY",
            ),
            ModelProfile(
                name="gemini-premium-default",
                provider_name="google_gemini",
                model=os.getenv("KABBALAH_GEMINI_MODEL", "gemini-2.5-pro"),
                roles={"Root_Orchestrator", "Domain_Coordinator"},
                capabilities={"chat", "reasoning"},
                context_window=32768,
                input_cost_per_1m_tokens=0.50,
                output_cost_per_1m_tokens=1.50,
                license_type="paga",
                location="cloud",
                tier="premium",
                api_key_env="GOOGLE_GEMINI_API_KEY",
            ),
            ModelProfile(
                name="mistral-premium-default",
                provider_name="mistral",
                model=os.getenv("KABBALAH_MISTRAL_MODEL", "mistral-large"),
                roles={"Root_Orchestrator", "Domain_Coordinator"},
                capabilities={"chat", "reasoning"},
                context_window=32768,
                input_cost_per_1m_tokens=2.0,
                output_cost_per_1m_tokens=6.0,
                license_type="paga",
                location="cloud",
                tier="premium",
                api_key_env="MISTRAL_API_KEY",
            ),
        ]
        return cls(
            profile
            for profile in profiles
            if profile.api_key_env is None or os.getenv(profile.api_key_env)
        )

    def available_for(
        self,
        *,
        role: str,
        capability: str,
        budget_hint: Optional[float] = None,
    ) -> list[ModelProfile]:
        """Return profiles matching role, capability, availability, and budget."""
        profiles = [
            profile
            for profile in self._profiles
            if profile.available
            and role in profile.roles
            and capability in profile.capabilities
            and (budget_hint is None or profile.total_cost_per_1m_tokens <= budget_hint)
        ]
        return sorted(profiles, key=self._selection_key)

    @staticmethod
    def _selection_key(profile: ModelProfile) -> tuple[int, float, str]:
        tier_order = {
            "local": 0,
            "fast": 1,
            "barato": 1,
            "cheap": 1,
            "agregador": 2,
            "aggregator": 2,
            "premium": 3,
        }
        return (
            tier_order.get(profile.tier, 2),
            profile.total_cost_per_1m_tokens,
            profile.name,
        )


class LLMGateway:
    """Select providers through the canonical capability registry."""

    def __init__(
        self,
        providers: Optional[Iterable[ProviderCandidate]] = None,
        *,
        factory: Optional[ProviderFactoryProtocol] = None,
        registry: Optional[CapabilityRegistry] = None,
        budget_manager: Optional[Any] = None,
    ):
        self.providers: List[ProviderCandidate] = list(providers or [])
        self.factory = factory
        self.registry = registry or CapabilityRegistry.default()
        self.budget_manager = budget_manager
        self._unavailable_profiles: dict[str, str] = {}

    @property
    def unavailable_profiles(self) -> dict[str, str]:
        """Return profiles marked unavailable in this gateway session."""
        return dict(self._unavailable_profiles)

    def mark_unavailable(self, profile: ModelProfile, error: str) -> None:
        """Mark a profile unavailable for subsequent selections."""
        self._unavailable_profiles[profile.name] = error
        logger.warning(
            "Marked provider profile unavailable: %s (%s): %s",
            profile.name,
            profile.provider_name,
            error,
        )

    def registrar_provider(self, provider: ProviderCandidate) -> None:
        """Register a legacy provider candidate."""
        self.providers.append(provider)

    def registrar_model(self, profile: ModelProfile) -> None:
        """Register a canonical model profile."""
        self.registry.register(profile)

    def select_provider(
        self,
        *,
        role: str,
        capability: str = "chat",
        budget_hint: Optional[float] = None,
        trace_id: str = "gateway:selection",
    ) -> ProviderSelection:
        """Select and instantiate a provider by role and capability."""
        selections = self.select_providers(
            role=role,
            capability=capability,
            budget_hint=budget_hint,
            trace_id=trace_id,
        )
        if not selections:
            raise ValueError(
                f"No provider profile available for role '{role}' and capability "
                f"'{capability}'. Run `kabbalah setup` or update the capability registry."
            )
        return selections[0]

    def select_providers(
        self,
        *,
        role: str,
        capability: str = "chat",
        budget_hint: Optional[float] = None,
        trace_id: str = "gateway:selection",
    ) -> list[ProviderSelection]:
        """Return ordered provider candidates for fallback-capable callers."""
        if self.factory is None:
            raise ValueError("LLMGateway requires a ProviderFactory to select real providers")

        candidates = self.registry.available_for(
            role=role,
            capability=capability,
            budget_hint=budget_hint,
        )
        candidates = [
            profile
            for profile in candidates
            if profile.name not in self._unavailable_profiles
        ]
        if not candidates:
            budget_msg = f" within budget {budget_hint}" if budget_hint is not None else ""
            raise ValueError(
                f"No provider profile available for role '{role}' and capability "
                f"'{capability}'{budget_msg}. Run `kabbalah setup` or update the "
                "capability registry."
            )

        selections: list[ProviderSelection] = []
        for profile in candidates:
            self._enforce_budget(profile, trace_id=trace_id)
            try:
                provider = self.factory.create_provider(
                    profile.provider_name,
                    **profile.provider_kwargs(),
                )
            except Exception as exc:
                self.mark_unavailable(profile, str(exc))
                continue
            selections.append(ProviderSelection(profile=profile, provider=provider))

        if not selections:
            raise ValueError(
                f"All provider profiles failed for role '{role}' and capability "
                f"'{capability}'. Unavailable: {self._unavailable_profiles}"
            )
        return selections

    def _enforce_budget(self, profile: ModelProfile, *, trace_id: str) -> None:
        if self.budget_manager is None:
            return
        decision = self.budget_manager.enforce_call(
            provider=profile.provider_name,
            projected_cost=0.0,
            trace_id=trace_id,
        )
        if not decision.allowed:
            logger.warning(
                "Budget exceeded in warn mode for provider %s: %s",
                profile.provider_name,
                decision.exceeded,
            )

    def selecionar_provider(
        self,
        role: Optional[str] = None,
        *,
        capability: str = "chat",
        budget_hint: Optional[float] = None,
        trace_id: str = "gateway:selection",
        required_capabilities: Optional[Set[str]] = None,
        risk_score: float = 0.0,
    ) -> Any:
        """Compatibility wrapper.

        With ``role`` it returns a real provider instance selected by the
        canonical registry. Without ``role`` it preserves the old
        ProviderCandidate selection behavior used by older tests/callers.
        """
        if role is not None:
            return self.select_provider(
                role=role,
                capability=capability,
                budget_hint=budget_hint,
                trace_id=trace_id,
            ).provider

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
