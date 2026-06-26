"""Integration tests for Kabbalah v2 hooks in existing modules."""

from kabbalah.contratos import ContratoSucesso
from kabbalah.intake_node import IntakeNode
from kabbalah.memory_subsystem import MemorySubsystem
from kabbalah.models import UserRequest
from kabbalah.root_orchestrator import RootOrchestrator
from kabbalah.tradutor_local import RiskZone


def test_intake_attaches_tradutor_local_metadata():
    intake = IntakeNode()
    request = UserRequest(
        project_name="Login",
        project_description="arrumar login quebrado e criar testes",
    )

    spec, _ = intake.parse_request(request)

    assert spec.translation_info["tradutor_local"]["zona"] == RiskZone.LIBERAR.value
    assert "pedido_tecnico" in spec.translation_info["tradutor_local"]


def test_memory_subsystem_records_antiprompt(tmp_path):
    memory = MemorySubsystem(jsonl_storage_path=str(tmp_path))

    antiprompt = memory.record_antiprompt(
        content="não bloquear pedido legítimo de teste",
        reason="false_refusal",
        trace_id="trace-1",
    )

    assert antiprompt.category == "anti-prompt"
    assert memory.query_knowledge("pedido legítimo")


def test_root_orchestrator_executes_with_success_contract_and_replanning():
    attempts = []
    orchestrator = RootOrchestrator()
    contrato = ContratoSucesso(
        contrato_id="c1",
        objetivo="gerar resultado",
        artefatos_obrigatorios=["result.md"],
    )

    def executor(plan):
        attempts.append(plan)
        if len(attempts) == 1:
            return {"success": False, "artefatos": {}}
        return {"success": True, "artefatos": {"result.md": "ok"}}

    result = orchestrator.execute_with_success_contract(
        plan={"task": "build"},
        executor=executor,
        contract=contrato,
        trace_id="trace-1",
        max_retries=3,
    )

    assert result.status.value == "success"
    assert len(attempts) == 2
