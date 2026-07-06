"""Tests for the pluggable risk assessor implementations in Qlipot."""

import base64
from unittest.mock import MagicMock

from kabbalah.llm_gateway import ModelProfile, ProviderSelection
from kabbalah.providers.base import ProviderResponse
from kabbalah.qlipot import Qlipot, QlipotStatus
from kabbalah.risk_assessor import HeuristicRiskAssessor, LLMRiskAssessor


def test_heuristic_risk_assessor_directly():
    assessor = HeuristicRiskAssessor()
    assert assessor.identity == "heuristic-offline"
    assert assessor.version == "wave10-2026.07"

    # Critical terms
    assert assessor.assess_risk("call_tool", {}, "delete production database") >= 0.96
    # Unicode bypass protection
    assert assessor.assess_risk("call_tool", {}, "ｄｅｌｅｔｅ production database") >= 0.96
    # Base64 protection
    payload = base64.b64encode(b"delete production token").decode()
    assert assessor.assess_risk("call_tool", {}, f"process: {payload}") >= 0.96
    # Benign
    assert assessor.assess_risk("read_file", {}, "read system documentation") <= 0.30


def test_heuristic_risk_assessor_injected_in_qlipot():
    assessor = HeuristicRiskAssessor()
    qlipot = Qlipot(risk_assessor=assessor)

    result = qlipot.avaliar_intencao(
        pedido="delete production database",
        ferramenta="call_tool",
        argumentos={},
    )
    assert result.risco >= 0.96
    assert result.status == QlipotStatus.BLOQUEADO
    assert "heuristic-offline" in result.assessor_version


def test_llm_risk_assessor_successful_json_parse():
    # Setup mocks for LLM selection
    mock_provider = MagicMock()
    mock_provider.execute_request.return_value = ProviderResponse(
        content='{"score": 0.85, "reason": "Highly suspicious deployment commands"}',
        model="gpt-4o",
        tokens_used=120,
        cost=0.001,
        latency_ms=250.0,
    )

    mock_profile = ModelProfile(
        name="openai-test",
        provider_name="openai",
        model="gpt-4o",
        roles={"Root_Orchestrator"},
        capabilities={"chat", "risk-judge"},
        context_window=8192,
        input_cost_per_1m_tokens=1.0,
        output_cost_per_1m_tokens=1.0,
        license_type="paga",
        location="cloud",
        tier="premium",
    )

    mock_gateway = MagicMock()
    mock_gateway.select_provider.return_value = ProviderSelection(
        profile=mock_profile,
        provider=mock_provider,
    )

    assessor = LLMRiskAssessor(gateway=mock_gateway)
    score = assessor.assess_risk("call_tool", {}, "deploy updates to production")

    assert score == 0.85
    assert assessor.identity == "llm-openai-test:gpt-4o"
    mock_gateway.select_provider.assert_called_once_with(
        role="Root_Orchestrator",
        capability="risk-judge",
    )


def test_llm_risk_assessor_fallback_on_invalid_json():
    mock_provider = MagicMock()
    # Returns text that is NOT valid JSON
    mock_provider.execute_request.return_value = ProviderResponse(
        content="I think this request is fine, score is probably 0.2.",
        model="gpt-4o",
        tokens_used=120,
        cost=0.001,
        latency_ms=250.0,
    )

    mock_profile = ModelProfile(
        name="openai-test",
        provider_name="openai",
        model="gpt-4o",
        roles={"Root_Orchestrator"},
        capabilities={"chat", "risk-judge"},
        context_window=8192,
        input_cost_per_1m_tokens=1.0,
        output_cost_per_1m_tokens=1.0,
        license_type="paga",
        location="cloud",
        tier="premium",
    )

    mock_gateway = MagicMock()
    mock_gateway.select_provider.return_value = ProviderSelection(
        profile=mock_profile,
        provider=mock_provider,
    )

    # Injecting custom fallback assessor to assert it is called
    mock_fallback = MagicMock(spec=HeuristicRiskAssessor)
    mock_fallback.identity = "mock-heuristic"
    mock_fallback.assess_risk.return_value = 0.99

    assessor = LLMRiskAssessor(gateway=mock_gateway, fallback_assessor=mock_fallback)
    score = assessor.assess_risk("call_tool", {}, "delete production database")

    # Should fall back to mock_fallback since JSON parsing fails
    assert score == 0.99
    assert assessor.identity == "fallback-mock-heuristic"
    mock_fallback.assess_risk.assert_called_once_with("call_tool", {}, "delete production database")


def test_llm_risk_assessor_fallback_on_api_exception():
    mock_gateway = MagicMock()
    # Simulate API connection exception on gateway selection or execution
    mock_gateway.select_provider.side_effect = RuntimeError("network timeout")

    mock_fallback = MagicMock(spec=HeuristicRiskAssessor)
    mock_fallback.identity = "mock-heuristic"
    mock_fallback.assess_risk.return_value = 0.99

    assessor = LLMRiskAssessor(gateway=mock_gateway, fallback_assessor=mock_fallback)
    score = assessor.assess_risk("call_tool", {}, "delete production database")

    # Should fall back to mock_fallback
    assert score == 0.99
    assert assessor.identity == "fallback-mock-heuristic"
    mock_fallback.assess_risk.assert_called_once_with("call_tool", {}, "delete production database")
