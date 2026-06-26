"""Tests for success contract integration in contract enforcement."""

from kabbalah.contract_enforcement import ContractEnforcementModule
from kabbalah.contratos import ContratoSucesso


def test_contract_enforcement_validates_success_contract():
    module = ContractEnforcementModule()
    contrato = ContratoSucesso(
        contrato_id="success-1",
        objetivo="gerar artefato",
        artefatos_obrigatorios=["result.md"],
    )
    module.register_success_contract("op", contrato)

    ok, error = module.validate_success_contract(
        "op",
        {"artefatos": {"result.md": "# ok"}},
        trace_id="trace-1",
    )

    assert ok is True
    assert error is None


def test_contract_enforcement_logs_success_contract_violation():
    module = ContractEnforcementModule()
    contrato = ContratoSucesso(
        contrato_id="success-1",
        objetivo="gerar artefato",
        artefatos_obrigatorios=["result.md"],
    )
    module.register_success_contract("op", contrato)

    ok, error = module.validate_success_contract("op", {"artefatos": {}}, trace_id="trace-1")

    assert ok is False
    assert "result.md" in error
    assert module.violation_log[-1].violation_type == "success_contract"
