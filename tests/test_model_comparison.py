"""Tests for model comparison service."""

from kabbalah.llm_gateway import LLMGateway, ModelProfile
from kabbalah.model_comparison import compare_models
from kabbalah.providers.mock_provider import MockProvider


class MockFactory:
    def __init__(self):
        self.created = []

    def create_provider(self, provider_name, **kwargs):
        self.created.append((provider_name, kwargs))
        return MockProvider(
            response_content=f"response from {provider_name}",
            latency_ms=1.0,
        )


def _profile(name, provider_name, model):
    return ModelProfile(
        name=name,
        provider_name=provider_name,
        model=model,
        roles={"Leaf_Builder"},
        capabilities={"chat"},
        context_window=4096,
        input_cost_per_1m_tokens=0.01,
        output_cost_per_1m_tokens=0.01,
        license_type="test",
        location="test",
        tier="fast",
    )


def test_compare_models_dispatches_same_task_to_multiple_mock_providers(monkeypatch):
    monkeypatch.setenv("KABBALAH_ALLOW_TEST_FAKE_PROVIDER", "1")
    gateway = LLMGateway(
        factory=MockFactory(),
        registry=None,
    )
    gateway.registry._profiles.clear()
    gateway.registrar_model(_profile("mock-a", "mock_a", "mock-model-1"))
    gateway.registrar_model(_profile("mock-b", "mock_b", "mock-model-2"))

    result = compare_models(
        task="Say hello",
        gateway=gateway,
        providers=["mock_a", "mock_b"],
        role="Leaf_Builder",
        capability="chat",
        max_tokens=20,
    )

    rows = result["comparisons"]
    assert [row["provider"] for row in rows] == ["mock_a", "mock_b"]
    assert rows[0]["response"] == "response from mock_a"
    assert rows[1]["response"] == "response from mock_b"
    assert rows[0]["tokens"] > 0
    assert result["summary"]["provider_count"] == 2
    assert result["summary"]["error_count"] == 0


def test_compare_models_returns_honest_error_for_unavailable_requested_provider(monkeypatch):
    monkeypatch.setenv("KABBALAH_ALLOW_TEST_FAKE_PROVIDER", "1")
    gateway = LLMGateway(factory=MockFactory(), registry=None)
    gateway.registry._profiles.clear()
    gateway.registrar_model(_profile("mock-a", "mock_a", "mock-model-1"))

    result = compare_models(
        task="Say hello",
        gateway=gateway,
        providers=["mock_a", "missing_provider"],
        role="Leaf_Builder",
        capability="chat",
    )

    rows = {row["provider"]: row for row in result["comparisons"]}
    assert rows["mock_a"]["error"] is None
    assert rows["missing_provider"]["error"] == (
        "Provider not available for this role/capability. Run `kabbalah setup` or update the registry."
    )
