"""Tests for the SillyTavern MCP bridge."""

import json

import pytest

from kabbalah.firewall_mcp import AcaoMCP, FirewallMCP, MCPDecision, MCPRequest, MCPRiskLevel, RegraMCP
from kabbalah.hitl import HITL, NivelUrgencia, SolicitacaoHITL, StatusAprovacao
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


def test_compatibility_aliases_exist_for_documented_bridge_names():
    assert StatusAprovacao.PENDING.value == "pending"
    assert RegraMCP(acao=AcaoMCP.READ_FILE, allowed_roles={"reader"}).acao == AcaoMCP.READ_FILE
    request = SolicitacaoHITL(
        agente_id="agent",
        acao=AcaoMCP.READ_FILE.value,
        risco=0.2,
        contexto={},
        trace_id="trace",
    )
    assert request.agente_id == "agent"


def test_qlipot_avaliar_intencao_exposes_confidence_and_risk():
    result = Qlipot().avaliar_intencao(
        pedido="ler o arquivo README para análise",
        ferramenta=AcaoMCP.READ_FILE.value,
        argumentos={"path": "README.md"},
    )

    assert 0 <= result.score_confianca <= 1
    assert result.risco < 0.45
    assert result.bloqueado is False


def test_qlipot_avaliar_uses_agent_temporal_memory(tmp_path):
    from kabbalah.memory_subsystem import MemorySubsystem

    memory = MemorySubsystem(jsonl_storage_path=str(tmp_path))
    qlipot = Qlipot(memory=memory)

    for idx in range(5):
        qlipot.registrar_acao_agente(
            agente_id="agent-1",
            acao="execute_command",
            parametros={"command": f"echo {idx}"},
        )

    result = qlipot.avaliar(
        agente_id="agent-1",
        acao="execute_command",
        parametros={"command": "echo final"},
    )

    assert result.score_contexto > 0
    assert result.score_final == min(1.0, result.score_atual + result.score_contexto)


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
async def test_bridge_hitl_pending_returns_ticket_contract(monkeypatch):
    import kabbalah_mcp_bridge as bridge

    def hitl_required(_: MCPRequest) -> MCPDecision:
        return MCPDecision(
            autorizado=False,
            motivo="HITL approval required or denied: No approval provider configured",
            trace_id="trace-hitl",
            agente_id="agent",
            ferramenta=AcaoMCP.EXECUTE_COMMAND.value,
            risk_level=MCPRiskLevel.HIGH,
            risk_score=0.8,
            hitl_required=True,
        )

    monkeypatch.setattr(bridge.firewall, "autorizar", hitl_required)

    response = await bridge._authorize_and_execute(
        acao=AcaoMCP.EXECUTE_COMMAND,
        agente_id="agent",
        papel_agente="operator",
        argumentos={"command": "pytest"},
        executor=lambda: "should not execute",
    )
    payload = json.loads(response)

    assert payload["error"] == "HITL_REQUIRED"
    assert payload["ticket_id"].startswith("hitl_")
    assert payload["message"] == "Ação requer aprovação humana. Use o endpoint de consulta para verificar status."

    status_response = await bridge.hitl_status(bridge.HITLStatusInput(ticket_id=payload["ticket_id"]))
    status_payload = json.loads(status_response)
    assert status_payload["ok"] is True
    assert status_payload["status"] == "pending"
    assert bridge.hitl.audit_log[-1].status == StatusAprovacao.PENDING
    assert bridge.hitl.audit_log[-1].trace_id == payload["ticket_id"]


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


@pytest.mark.asyncio
async def test_bridge_records_successful_action_in_temporal_memory(monkeypatch):
    import kabbalah_mcp_bridge as bridge

    recorded = []

    def record_action(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr(bridge.qlipot, "registrar_acao_agente", record_action)
    monkeypatch.setattr(
        bridge.firewall,
        "autorizar",
        lambda _: MCPDecision(
            autorizado=True,
            motivo="authorized",
            trace_id="trace-ok",
            agente_id="agent",
            ferramenta=AcaoMCP.READ_FILE.value,
            risk_level=MCPRiskLevel.LOW,
            risk_score=0.1,
        ),
    )

    response = await bridge._authorize_and_execute(
        acao=AcaoMCP.READ_FILE,
        agente_id="agent",
        papel_agente="reader",
        argumentos={"path": "README.md"},
        executor=lambda: {"content": "ok"},
    )
    payload = json.loads(response)

    assert payload["ok"] is True
    assert recorded == [
        {
            "agente_id": "agent",
            "acao": AcaoMCP.READ_FILE.value,
            "parametros": {
                "argumentos": {"path": "README.md"},
                "risk_score": 0.1,
                "risk_level": MCPRiskLevel.LOW.value,
                "result_type": "dict",
            },
        }
    ]
