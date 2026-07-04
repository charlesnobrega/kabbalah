"""Wave-2 hardening tests: persistent, auditable agent contracts."""

import sqlite3
import threading

from kabbalah.contrato_store import (
    EVENTO_AUSENCIA_CONTRATO,
    EVENTO_VIOLACAO,
    ContratoStore,
)
from kabbalah.contratos import ContractStatus, Contratos, VerificationOutcome
from kabbalah.hitl import HITL


def _propor_e_assinar(contratos, provedor="worker", acao="call_tool", limites=None, task_id=None):
    contrato = contratos.propor(
        requisitante="coordinator",
        provedor=provedor,
        acao=acao,
        limites=limites or {},
        papeis=["coordinator"],
        task_id=task_id,
    )
    assert contratos.assinar(contrato.id, provedor) is True
    return contrato


def test_active_contract_survives_restart(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))
    contrato = _propor_e_assinar(contratos, limites={"max_calls": 3})

    reloaded = Contratos(store=ContratoStore(db))

    assert contrato.id in reloaded.contratos
    assert reloaded.contratos[contrato.id].status == ContractStatus.ATIVO
    assert reloaded.verificar("worker", "call_tool") is True


def test_all_statuses_are_persisted(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))

    ativo = _propor_e_assinar(contratos, acao="read_file")
    concluido = _propor_e_assinar(contratos, acao="write_file", task_id="task-done")
    contratos.complete_task("task-done", "coordinator")
    violado = _propor_e_assinar(contratos, acao="network_request", limites={"max_calls": 0})
    contratos.verificar("worker", "network_request")
    revogado = _propor_e_assinar(contratos, acao="call_tool")
    contratos.revogar(revogado.id, "human", "policy change")
    rejeitado = contratos.propor("coordinator", "worker", "database_query", {}, ["coordinator"])
    contratos.rejeitar(rejeitado.id, "worker", "busy")

    persisted = {c.id: c.status for c in ContratoStore(db).load_all()}

    assert persisted[ativo.id] == ContractStatus.ATIVO
    assert persisted[concluido.id] == ContractStatus.CONCLUIDO
    assert persisted[violado.id] == ContractStatus.VIOLADO
    assert persisted[revogado.id] == ContractStatus.REVOGADO
    assert persisted[rejeitado.id] == ContractStatus.REJEITADO


def test_provedor_acao_status_index_exists(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    ContratoStore(db)

    with sqlite3.connect(db) as conn:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list('contratos')")}

    assert "idx_contratos_provedor_acao_status" in indexes


def test_max_calls_is_atomic_under_concurrency(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))
    max_calls = 5
    _propor_e_assinar(contratos, limites={"max_calls": max_calls})

    granted = []
    barrier = threading.Barrier(16)

    def worker():
        barrier.wait()
        if contratos.verificar("worker", "call_tool"):
            granted.append(1)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(granted) == max_calls
    stored = ContratoStore(db).load_all()[0]
    assert stored.chamadas == max_calls


def test_max_calls_thread_safe_without_store():
    contratos = Contratos()
    max_calls = 5
    _propor_e_assinar(contratos, limites={"max_calls": max_calls})

    granted = []
    barrier = threading.Barrier(16)

    def worker():
        barrier.wait()
        if contratos.verificar("worker", "call_tool"):
            granted.append(1)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(granted) == max_calls


def test_violation_is_persisted_in_append_only_log(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    store = ContratoStore(db)
    contratos = Contratos(store=store)
    contrato = _propor_e_assinar(contratos, limites={"max_calls": 1})

    assert contratos.verificar("worker", "call_tool") is True
    assert contratos.verificar("worker", "call_tool") is False

    events = store.list_events(tipo=EVENTO_VIOLACAO)
    assert len(events) == 1
    assert events[0]["contrato_id"] == contrato.id
    assert events[0]["motivo"] == "Limite max_calls excedido"
    assert not hasattr(store, "delete_event")
    assert not hasattr(store, "update_event")


def test_absence_is_recorded_separately_from_violation(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    store = ContratoStore(db)
    hitl = HITL()
    contratos = Contratos(hitl=hitl, store=store)

    assert contratos.verificar_detalhado("worker", "call_tool") == VerificationOutcome.NO_CONTRACT
    contratos.registrar_violacao("worker", "call_tool", "Ação sem contrato ativo")

    assert store.list_events(tipo=EVENTO_VIOLACAO) == []
    ausencias = store.list_events(tipo=EVENTO_AUSENCIA_CONTRATO)
    assert len(ausencias) == 1
    assert ausencias[0]["agente_id"] == "worker"
    assert hitl.audit_log == []


def test_verificar_detalhado_outcomes(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))

    assert contratos.verificar_detalhado("worker", "call_tool") == VerificationOutcome.NO_CONTRACT

    contrato = _propor_e_assinar(contratos, limites={"max_calls": 1})
    assert contratos.verificar_detalhado("worker", "call_tool") == VerificationOutcome.ALLOWED
    assert contratos.verificar_detalhado("worker", "call_tool") == VerificationOutcome.LIMIT_EXCEEDED
    assert contratos.contratos[contrato.id].status == ContractStatus.VIOLADO


def test_verificar_detalhado_expired_contract(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))
    contrato = _propor_e_assinar(contratos, limites={"timeout_min": 1})
    contrato.criado_em -= 120

    assert contratos.verificar_detalhado("worker", "call_tool") == VerificationOutcome.EXPIRED
    assert contratos.contratos[contrato.id].status == ContractStatus.VIOLADO


def test_violated_contract_stays_violated_after_restart(tmp_path):
    db = tmp_path / "contracts.sqlite3"
    contratos = Contratos(store=ContratoStore(db))
    _propor_e_assinar(contratos, limites={"max_calls": 1})
    assert contratos.verificar("worker", "call_tool") is True
    assert contratos.verificar("worker", "call_tool") is False

    reloaded = Contratos(store=ContratoStore(db))

    assert reloaded.verificar("worker", "call_tool") is False
    assert reloaded.verificar_detalhado("worker", "call_tool") == VerificationOutcome.NO_CONTRACT
