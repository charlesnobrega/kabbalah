"""Wave-2 bridge hardening tests: contract persistence and absence auditing."""

import importlib
from pathlib import Path

from kabbalah.contrato_store import EVENTO_AUSENCIA_CONTRATO, EVENTO_VIOLACAO
from kabbalah.firewall_mcp import AcaoMCP, MCPRequest


def reload_bridge(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KABBALAH_BRIDGE_ALLOWED_DIRS", str(tmp_path))
    monkeypatch.setenv("KABBALAH_BRIDGE_STATE_DB", str(tmp_path / "bridge_state.sqlite3"))
    import kabbalah_mcp_bridge as bridge

    return importlib.reload(bridge)


def _mcp_request(agente_id: str, ferramenta: str) -> MCPRequest:
    return MCPRequest(
        agente_id=agente_id,
        ferramenta=ferramenta,
        argumentos={},
        contrato_id="bridge",
        trace_id="trace",
        metadata={},
    )


def test_signed_contract_survives_bridge_restart(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)
    contrato = bridge.contratos.propor(
        requisitante="coordinator",
        provedor="restart-agent",
        acao=AcaoMCP.READ_FILE.value,
        limites={"max_calls": 5},
        papeis=["coordinator"],
    )
    assert bridge.contratos.assinar(contrato.id, "restart-agent") is True

    bridge = reload_bridge(monkeypatch, tmp_path)

    allowed, reason = bridge._contract_checker(_mcp_request("restart-agent", AcaoMCP.READ_FILE.value))
    assert allowed is True
    assert reason is None


def test_contract_absence_is_audited_without_violation(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)

    allowed, reason = bridge._contract_checker(_mcp_request("no-contract-agent", AcaoMCP.READ_FILE.value))

    assert allowed is False
    assert "Nenhum contrato ativo" in reason
    ausencias = bridge.contratos.store.list_events(tipo=EVENTO_AUSENCIA_CONTRATO)
    assert len(ausencias) == 1
    assert ausencias[0]["agente_id"] == "no-contract-agent"
    assert bridge.contratos.store.list_events(tipo=EVENTO_VIOLACAO) == []
    assert bridge.hitl.audit_log == []


def test_contract_verifier_absence_does_not_mark_violation(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)

    assert bridge._contract_verifier("agent-x", "call_tool") is False

    assert bridge.contratos.store.list_events(tipo=EVENTO_VIOLACAO) == []
    assert len(bridge.contratos.store.list_events(tipo=EVENTO_AUSENCIA_CONTRATO)) == 1


def test_exhausted_contract_reports_violation_reason(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)
    contrato = bridge.contratos.propor(
        requisitante="coordinator",
        provedor="limited-agent",
        acao=AcaoMCP.READ_FILE.value,
        limites={"max_calls": 1},
        papeis=["coordinator"],
    )
    assert bridge.contratos.assinar(contrato.id, "limited-agent") is True

    allowed, _ = bridge._contract_checker(_mcp_request("limited-agent", AcaoMCP.READ_FILE.value))
    assert allowed is True
    allowed, reason = bridge._contract_checker(_mcp_request("limited-agent", AcaoMCP.READ_FILE.value))

    assert allowed is False
    assert "LIMIT_EXCEEDED" in reason
    violations = bridge.contratos.store.list_events(tipo=EVENTO_VIOLACAO)
    assert len(violations) == 1
    assert violations[0]["contrato_id"] == contrato.id
