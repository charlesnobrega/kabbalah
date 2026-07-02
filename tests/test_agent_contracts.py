import pytest

from kabbalah.contratos import ContractStatus, Contratos
from kabbalah.hitl import HITL


def test_contract_proposal_requires_coordinator_role():
    contratos = Contratos()

    with pytest.raises(PermissionError):
        contratos.propor(
            requisitante="agent-a",
            provedor="agent-b",
            acao="call_tool",
            limites={"max_calls": 1},
            papeis=["viewer"],
        )


def test_contract_lifecycle_active_verify_and_complete():
    contratos = Contratos()

    contrato = contratos.propor(
        requisitante="coordinator",
        provedor="worker",
        acao="call_tool",
        limites={"max_calls": 2},
        papeis=["coordinator"],
        task_id="task-1",
    )

    assert contrato.status == ContractStatus.PROPOSTO
    assert contratos.assinar(contrato.id, "worker") is True
    assert contrato.status == ContractStatus.ATIVO
    assert contratos.verificar("worker", "call_tool") is True
    assert contratos.verificar("worker", "call_tool") is True
    assert contratos.verificar("worker", "call_tool") is False
    assert contrato.status == ContractStatus.VIOLADO

    completed = contratos.complete_task("task-1", "coordinator")
    assert completed == []


def test_contract_reject_and_revoke():
    contratos = Contratos()
    rejected = contratos.propor("coord", "provider", "network_request", {}, ["coordinator"])
    revoked = contratos.propor("coord", "provider", "read_file", {}, ["coordinator"])

    assert contratos.rejeitar(rejected.id, "provider", "busy") is True
    assert rejected.status == ContractStatus.REJEITADO
    assert contratos.revogar(revoked.id, "human", "policy change") is True
    assert revoked.status == ContractStatus.REVOGADO


def test_contract_violation_emits_callback_and_hitl():
    events = []
    hitl = HITL()
    contratos = Contratos(hitl=hitl)
    contratos.registrar_callback("violacao", lambda event, data: events.append((event, data)))
    contrato = contratos.propor("coord", "worker", "execute_command", {"max_calls": 1}, ["coordinator"])
    assert contratos.assinar(contrato.id, "worker") is True

    assert contratos.verificar("worker", "execute_command") is True
    assert contratos.verificar("worker", "execute_command") is False

    assert events[0][0] == "violacao"
    assert events[0][1]["contrato_id"] == contrato.id
    assert hitl.audit_log[-1].status.value == "pending"
