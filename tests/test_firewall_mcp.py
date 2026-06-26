"""Tests for MCP firewall authorization."""

from kabbalah.firewall_mcp import FirewallMCP, MCPRequest, MCPRiskLevel
from kabbalah.hitl import HITL


def test_firewall_authorizes_low_risk_request_when_rbac_and_contract_pass():
    firewall = FirewallMCP(
        rbac_checker=lambda request: (True, None),
        contract_checker=lambda request: (True, None),
        risk_assessor=lambda request: (MCPRiskLevel.LOW, 0.2, "baixo risco"),
    )
    request = MCPRequest(
        agente_id="agent-1",
        ferramenta="filesystem.read",
        argumentos={"path": "README.md"},
        contrato_id="contract-1",
        trace_id="trace-1",
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is True
    assert decision.risk_level == MCPRiskLevel.LOW
    assert decision.trace_id == "trace-1"
    assert firewall.audit_log[-1].autorizado is True


def test_firewall_denies_when_rbac_fails():
    firewall = FirewallMCP(
        rbac_checker=lambda request: (False, "role sem permissao"),
        contract_checker=lambda request: (True, None),
        risk_assessor=lambda request: (MCPRiskLevel.LOW, 0.2, "baixo risco"),
    )
    request = MCPRequest(
        agente_id="agent-1",
        ferramenta="filesystem.write",
        argumentos={},
        contrato_id="contract-1",
        trace_id="trace-2",
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is False
    assert decision.motivo == "role sem permissao"


def test_firewall_denies_when_contract_fails():
    firewall = FirewallMCP(
        rbac_checker=lambda request: (True, None),
        contract_checker=lambda request: (False, "contrato invalido"),
        risk_assessor=lambda request: (MCPRiskLevel.LOW, 0.2, "baixo risco"),
    )
    request = MCPRequest(
        agente_id="agent-1",
        ferramenta="filesystem.write",
        argumentos={},
        contrato_id="contract-1",
        trace_id="trace-3",
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is False
    assert decision.motivo == "contrato invalido"


def test_firewall_requires_hitl_for_high_risk_and_allows_when_approved():
    hitl = HITL(approval_provider=lambda request: True)
    firewall = FirewallMCP(
        rbac_checker=lambda request: (True, None),
        contract_checker=lambda request: (True, None),
        risk_assessor=lambda request: (MCPRiskLevel.HIGH, 0.8, "alto risco"),
        hitl=hitl,
    )
    request = MCPRequest(
        agente_id="agent-1",
        ferramenta="shell.exec",
        argumentos={"command": "pytest"},
        contrato_id="contract-1",
        trace_id="trace-4",
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is True
    assert decision.hitl_required is True
    assert hitl.audit_log[-1].trace_id == "trace-4"


def test_firewall_requires_hitl_for_critical_risk_and_denies_without_approval():
    hitl = HITL(approval_provider=lambda request: False)
    firewall = FirewallMCP(
        rbac_checker=lambda request: (True, None),
        contract_checker=lambda request: (True, None),
        risk_assessor=lambda request: (MCPRiskLevel.CRITICAL, 0.98, "critico"),
        hitl=hitl,
    )
    request = MCPRequest(
        agente_id="agent-1",
        ferramenta="shell.exec",
        argumentos={"command": "deploy"},
        contrato_id="contract-1",
        trace_id="trace-5",
    )

    decision = firewall.autorizar(request)

    assert decision.autorizado is False
    assert decision.hitl_required is True
    assert "HITL" in decision.motivo
