"""Tests for the canonical LLM gateway and capability registry."""

import pytest

from kabbalah.budget_manager import BudgetExceededError, BudgetLedger, BudgetManager
from kabbalah.llm_gateway import CapabilityRegistry, LLMGateway, ModelProfile
from kabbalah.providers.google_gemini_provider import GoogleGeminiProvider
from kabbalah.providers.mistral_provider import MistralProvider
from kabbalah.providers.openai_provider import OpenAIProvider


class DummyProvider:
    def __init__(self, name: str):
        self.name = name


class RecordingFactory:
    def __init__(self):
        self.created = []

    def create_provider(self, provider_name: str, **kwargs):
        self.created.append((provider_name, kwargs))
        return DummyProvider(provider_name)


class FailingFirstFactory(RecordingFactory):
    def create_provider(self, provider_name: str, **kwargs):
        self.created.append((provider_name, kwargs))
        if provider_name == "ollama_local":
            raise ConnectionError("ollama offline")
        return DummyProvider(provider_name)


def test_gateway_selects_cheapest_available_profile_by_role_and_capability():
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="ollama-qwen",
            provider_name="ollama_local",
            model="qwen2.5-coder:7b",
            roles={"Leaf_Builder"},
            capabilities={"chat", "code"},
            context_window=32768,
            input_cost_per_1m_tokens=0.0,
            output_cost_per_1m_tokens=0.0,
            license_type="open",
            location="local",
            tier="local",
            backend="cpu",
            quant="q4_K_M",
        )
    )
    registry.register(
        ModelProfile(
            name="premium-openai",
            provider_name="openai",
            model="gpt-4.1",
            roles={"Root_Orchestrator", "Leaf_Builder"},
            capabilities={"chat", "reasoning"},
            context_window=128000,
            input_cost_per_1m_tokens=2.0,
            output_cost_per_1m_tokens=8.0,
            license_type="paga",
            location="cloud",
            tier="premium",
        )
    )

    factory = RecordingFactory()
    gateway = LLMGateway(factory=factory, registry=registry)

    selection = gateway.select_provider(role="Leaf_Builder", capability="code")

    assert selection.profile.name == "ollama-qwen"
    assert selection.provider.name == "ollama_local"
    assert factory.created == [
        (
            "ollama_local",
            {"model": "qwen2.5-coder:7b", "base_url": None},
        )
    ]


def test_gateway_returns_ordered_provider_candidates_for_leaf_fallback():
    registry = CapabilityRegistry(
        [
            ModelProfile(
                name="local",
                provider_name="ollama_local",
                model="llama3.1",
                roles={"Leaf_Builder"},
                capabilities={"code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.0,
                output_cost_per_1m_tokens=0.0,
                license_type="open",
                location="local",
                tier="local",
            ),
            ModelProfile(
                name="groq",
                provider_name="groq_compatible",
                model="llama-3.1-8b-instant",
                roles={"Leaf_Builder"},
                capabilities={"code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.05,
                output_cost_per_1m_tokens=0.08,
                license_type="agregador",
                location="cloud",
                tier="fast",
            ),
        ]
    )

    selections = LLMGateway(factory=RecordingFactory(), registry=registry).select_providers(
        role="Leaf_Builder",
        capability="code",
        trace_id="run:branch:leaf",
    )

    assert [selection.profile.name for selection in selections] == ["local", "groq"]


def test_gateway_skips_instantiation_failure_and_marks_profile_unavailable():
    registry = CapabilityRegistry(
        [
            ModelProfile(
                name="local",
                provider_name="ollama_local",
                model="llama3.1",
                roles={"Leaf_Builder"},
                capabilities={"code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.0,
                output_cost_per_1m_tokens=0.0,
                license_type="open",
                location="local",
                tier="local",
            ),
            ModelProfile(
                name="groq",
                provider_name="groq_compatible",
                model="llama-3.1-8b-instant",
                roles={"Leaf_Builder"},
                capabilities={"code"},
                context_window=8192,
                input_cost_per_1m_tokens=0.05,
                output_cost_per_1m_tokens=0.08,
                license_type="agregador",
                location="cloud",
                tier="fast",
            ),
        ]
    )
    gateway = LLMGateway(factory=FailingFirstFactory(), registry=registry)

    selection = gateway.select_provider(
        role="Leaf_Builder",
        capability="code",
        trace_id="run:branch:leaf",
    )

    assert selection.profile.name == "groq"
    assert "local" in gateway.unavailable_profiles


def test_gateway_passes_profile_pricing_to_provider_factory():
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="groq",
            provider_name="groq_compatible",
            model="llama-3.1-8b-instant",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=8192,
            input_cost_per_1m_tokens=0.05,
            output_cost_per_1m_tokens=0.08,
            license_type="agregador",
            location="cloud",
            tier="fast",
            base_url="https://api.groq.com/openai/v1",
        )
    )
    factory = RecordingFactory()

    LLMGateway(factory=factory, registry=registry).select_provider(
        role="Leaf_Builder",
        capability="chat",
    )

    assert factory.created == [
        (
            "groq_compatible",
            {
                "model": "llama-3.1-8b-instant",
                "base_url": "https://api.groq.com/openai/v1",
                "input_cost_per_1m_tokens": 0.05,
                "output_cost_per_1m_tokens": 0.08,
            },
        )
    ]


def test_gateway_escalates_to_premium_when_role_requires_it():
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="local-chat",
            provider_name="ollama_local",
            model="llama3.1",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=8192,
            input_cost_per_1m_tokens=0.0,
            output_cost_per_1m_tokens=0.0,
            license_type="open",
            location="local",
            tier="local",
        )
    )
    registry.register(
        ModelProfile(
            name="premium-root",
            provider_name="openai",
            model="gpt-4.1",
            roles={"Root_Orchestrator"},
            capabilities={"chat", "reasoning"},
            context_window=128000,
            input_cost_per_1m_tokens=2.0,
            output_cost_per_1m_tokens=8.0,
            license_type="paga",
            location="cloud",
            tier="premium",
        )
    )

    selection = LLMGateway(factory=RecordingFactory(), registry=registry).select_provider(
        role="Root_Orchestrator",
        capability="reasoning",
    )

    assert selection.profile.name == "premium-root"


def test_gateway_reports_clear_error_for_unknown_capability():
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="chat-only",
            provider_name="groq_compatible",
            model="llama-3.1-8b-instant",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=8192,
            input_cost_per_1m_tokens=0.05,
            output_cost_per_1m_tokens=0.08,
            license_type="agregador",
            location="cloud",
            tier="fast",
        )
    )

    gateway = LLMGateway(factory=RecordingFactory(), registry=registry)

    with pytest.raises(ValueError, match="Leaf_Builder.*vision"):
        gateway.select_provider(role="Leaf_Builder", capability="vision")


def test_budget_hint_filters_profiles_by_total_cost_per_1m_tokens():
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="cheap",
            provider_name="groq_compatible",
            model="cheap-model",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=8192,
            input_cost_per_1m_tokens=0.05,
            output_cost_per_1m_tokens=0.05,
            license_type="agregador",
            location="cloud",
            tier="fast",
        )
    )
    registry.register(
        ModelProfile(
            name="expensive",
            provider_name="openai",
            model="expensive-model",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=128000,
            input_cost_per_1m_tokens=5.0,
            output_cost_per_1m_tokens=15.0,
            license_type="paga",
            location="cloud",
            tier="premium",
        )
    )

    selection = LLMGateway(factory=RecordingFactory(), registry=registry).select_provider(
        role="Leaf_Builder",
        capability="chat",
        budget_hint=1.0,
    )

    assert selection.profile.name == "cheap"


def test_default_registry_skips_cloud_profiles_without_api_keys(monkeypatch):
    for env_name in (
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "SAMBANOVA_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_GEMINI_API_KEY",
        "MISTRAL_API_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)

    registry = CapabilityRegistry.default()
    provider_names = {profile.provider_name for profile in registry.list_profiles()}

    assert "ollama_local" in provider_names
    assert "openrouter" not in provider_names
    assert "cerebras" not in provider_names


def test_default_registry_includes_cloud_profiles_when_api_key_exists(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    registry = CapabilityRegistry.default()
    provider_names = {profile.provider_name for profile in registry.list_profiles()}

    assert "openrouter" in provider_names


def test_default_registry_premium_models_match_native_provider_allowlists(monkeypatch):
    for env_name in (
        "KABBALAH_OPENAI_MODEL",
        "KABBALAH_GEMINI_MODEL",
        "KABBALAH_MISTRAL_MODEL",
    ):
        monkeypatch.delenv(env_name, raising=False)
    for env_name in (
        "OPENAI_API_KEY",
        "GOOGLE_GEMINI_API_KEY",
        "MISTRAL_API_KEY",
    ):
        monkeypatch.setenv(env_name, "test-key")

    registry = CapabilityRegistry.default()
    profiles_by_provider = {
        profile.provider_name: profile
        for profile in registry.list_profiles()
        if profile.provider_name in {"openai", "google_gemini", "mistral"}
    }

    assert profiles_by_provider["openai"].model in OpenAIProvider.PRICING
    assert profiles_by_provider["google_gemini"].model in GoogleGeminiProvider.PRICING
    assert profiles_by_provider["mistral"].model in MistralProvider.PRICING


def test_default_registry_uses_current_openai_compatible_provider_models(monkeypatch):
    for env_name in (
        "KABBALAH_CEREBRAS_MODEL",
        "KABBALAH_SAMBANOVA_MODEL",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    monkeypatch.setenv("SAMBANOVA_API_KEY", "test-key")

    registry = CapabilityRegistry.default()
    profiles_by_provider = {
        profile.provider_name: profile
        for profile in registry.list_profiles()
        if profile.provider_name in {"cerebras", "sambanova"}
    }

    assert profiles_by_provider["cerebras"].base_url == "https://api.cerebras.ai/v1"
    assert profiles_by_provider["cerebras"].model == "gpt-oss-120b"
    assert profiles_by_provider["sambanova"].base_url == "https://api.sambanova.ai/v1"
    assert profiles_by_provider["sambanova"].model == "Meta-Llama-3.3-70B-Instruct"


def test_gateway_warns_budget_excess_but_returns_provider_in_warn_mode(tmp_path):
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="groq",
            provider_name="groq_compatible",
            model="llama-3.1-8b-instant",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=8192,
            input_cost_per_1m_tokens=0.05,
            output_cost_per_1m_tokens=0.08,
            license_type="agregador",
            location="cloud",
            tier="fast",
        )
    )
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="groq_compatible",
        model="llama-3.1-8b-instant",
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        cost=0.02,
        trace_id="run-budget:branch:leaf-a",
    )
    manager = BudgetManager(
        ledger,
        provider_limits_usd={"groq_compatible": 0.01},
        mode="warn",
    )

    selection = LLMGateway(
        factory=RecordingFactory(),
        registry=registry,
        budget_manager=manager,
    ).select_provider(
        role="Leaf_Builder",
        capability="chat",
        trace_id="run-budget:branch:leaf-b",
    )

    assert selection.profile.name == "groq"


def test_gateway_blocks_budget_excess_in_block_mode(tmp_path):
    registry = CapabilityRegistry()
    registry.register(
        ModelProfile(
            name="openrouter",
            provider_name="openrouter",
            model="openai/gpt-4o-mini",
            roles={"Leaf_Builder"},
            capabilities={"chat"},
            context_window=128000,
            input_cost_per_1m_tokens=0.15,
            output_cost_per_1m_tokens=0.60,
            license_type="agregador",
            location="cloud",
            tier="agregador",
        )
    )
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="openrouter",
        model="openai/gpt-4o-mini",
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        cost=0.20,
        trace_id="run-budget:branch:leaf-a",
    )
    manager = BudgetManager(
        ledger,
        run_limit_usd=0.10,
        mode="block",
    )

    with pytest.raises(BudgetExceededError):
        LLMGateway(
            factory=RecordingFactory(),
            registry=registry,
            budget_manager=manager,
        ).select_provider(
            role="Leaf_Builder",
            capability="chat",
            trace_id="run-budget:branch:leaf-b",
        )
