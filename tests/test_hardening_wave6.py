"""Wave-6 hardening tests: RBAC deny-by-default and logged enforcement."""

import pytest

from kabbalah.firewall_mcp import FirewallMCP, MCPRequest, MCPRiskLevel, permitir_tudo
from kabbalah.fsm_enforcement import (
    FSMEnforcementModule,
    Operation,
    OperationalMode,
    OperationType,
)


def _request(trace_id: str = "trace-w6") -> MCPRequest:
    return MCPRequest(
        agente_id="agent",
        ferramenta="filesystem.read",
        argumentos={"path": "README.md"},
        contrato_id="contract",
        trace_id=trace_id,
    )


def test_firewall_denies_by_default_without_any_checker():
    firewall = FirewallMCP()

    decision = firewall.autorizar(_request())

    assert decision.autorizado is False
    assert "negado por padrão" in decision.motivo


def test_firewall_denies_by_default_without_contract_checker():
    firewall = FirewallMCP(rbac_checker=permitir_tudo)

    decision = firewall.autorizar(_request())

    assert decision.autorizado is False
    assert "negado por padrão" in decision.motivo


def test_permitir_tudo_makes_permissiveness_explicit():
    firewall = FirewallMCP(
        rbac_checker=permitir_tudo,
        contract_checker=permitir_tudo,
        risk_assessor=lambda request: (MCPRiskLevel.LOW, 0.1, "low"),
    )

    decision = firewall.autorizar(_request())

    assert decision.autorizado is True


def test_main_enforcement_path_logs_blocked_operations():
    module = FSMEnforcementModule()
    operation = Operation(
        operation_type=OperationType.MEMORY_RESET,
        operation_name="reset_memory",
    )

    allowed = module.check_operation_allowed(operation, OperationalMode.DAY2)

    assert allowed is False
    assert len(module.violation_log) == 1
    assert module.violation_log[0].violation_type == "BOOTSTRAP_OPERATION_IN_DAY2"


def test_allowed_operation_does_not_log_violation():
    module = FSMEnforcementModule()
    operation = Operation(
        operation_type=OperationType.QUERY_OPERATION,
        operation_name="query",
    )

    assert module.check_operation_allowed(operation, OperationalMode.DAY2) is True
    assert module.violation_log == []


def test_with_logging_variant_is_deprecated_and_does_not_double_log():
    module = FSMEnforcementModule()
    operation = Operation(
        operation_type=OperationType.MEMORY_RESET,
        operation_name="reset_memory",
    )

    with pytest.warns(DeprecationWarning):
        allowed, message = module.check_operation_allowed_with_logging(operation, OperationalMode.DAY2)

    assert allowed is False
    assert message is not None
    assert len(module.violation_log) == 1
