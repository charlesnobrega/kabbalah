"""Tests for the SillyTavern MCP bridge."""

import json

import pytest

from kabbalah.firewall_mcp import AcaoMCP, FirewallMCP, MCPDecision, MCPRequest, MCPRiskLevel
from kabbalah.hitl import HITL, NivelUrgencia
from kabbalah.qlipot import Qlipot


def test_acao_mcp_maps_bridge_tools():
    assert AcaoMCP.READ_FILE.value == "read_file"
    assert AcaoMCP.EXECUTE_COMMAND.value == "execute_command"
    assert AcaoMCP.NETWORK_REQUEST.value == "network_request"


def test_hitl_solicitar_sync_wrapper_denies_without_provider():
    hitl = HITL()

    decision = hitl.solicitar(
        agente_id="agent",
        acao=AcaoMCP.EXECUTE_COMMAND,
        risco=0.8,
        contexto={},
        trace_id="trace-1",
        urgencia=NivelUrgencia.ALTA,
    )

    assert decision.aprovado is False
    assert "approval provider" in decision.motivo.lower()


def test_qlipot_avaliar_intencao_exposes_confidence_and_risk():
    result = Qlipot().avaliar_intencao(
        pedido="ler o arquivo README para análise",
        ferramenta=AcaoMCP.READ_FILE.value,
        argumentos={"path": "README.md"},
    )

    assert 0 <= result.score_confianca <= 1
    assert result.risco < 0.45
    assert result.bloqueado is False


def test_firewall_uses_bridge_risk_metadata():
    firewall = FirewallMCP(hitl=HITL(approval_provider=lambda request: True))
    request = MCPRequest(
        agente_id="agent",
        ferramenta=AcaoMCP.EXECUTE_COMMAND.value,
        argumentos={"command": "pytest"},
        contrato_id="sillytavern-bridge",
        trace_id="trace-1",
        metadata={"risco": 0.8, "score_confianca": 0.2},
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is True
    assert decision.hitl_required is True
    assert decision.risk_level == MCPRiskLevel.HIGH


@pytest.mark.asyncio
async def test_bridge_authorization_denial_returns_mcp_error(monkeypatch, tmp_path):
    import kabbalah_mcp_bridge as bridge

    def deny(_: MCPRequest) -> MCPDecision:
        return MCPDecision(
            autorizado=False,
            motivo="RBAC denied",
            trace_id="trace-denied",
            agente_id="agent",
            ferramenta=AcaoMCP.READ_FILE.value,
            risk_level=MCPRiskLevel.LOW,
            risk_score=0.2,
        )

    monkeypatch.setattr(bridge.firewall, "autorizar", deny)

    response = await bridge._authorize_and_execute(
        acao=AcaoMCP.READ_FILE,
        agente_id="agent",
        papel_agente="reader",
        argumentos={"path": str(tmp_path / "missing.txt")},
        executor=lambda: "should not execute",
    )
    payload = json.loads(response)

    assert payload["ok"] is False
    assert payload["error"] == "Acesso Bloqueado: Zona de Isolamento"


@pytest.mark.asyncio
async def test_bridge_read_file_happy_path(tmp_path):
    import kabbalah_mcp_bridge as bridge

    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")

    response = await bridge.read_file(
        bridge.ReadFileInput(path=str(file_path), agente_id="agent", papel_agente="reader")
    )
    payload = json.loads(response)

    assert payload["ok"] is True
    assert payload["result"]["content"] == "hello"
