"""Tests for Kabbalah v2 modules from the implementation specification."""

from kabbalah.autonomy_loop import AutonomyLoop, LoopStatus
from kabbalah.contratos import ContratoSucesso
from kabbalah.critic_node import CriticNode, CriticStatus
from kabbalah.llm_gateway import LLMGateway, ProviderCandidate
from kabbalah.qlipot import Qlipot, QlipotStatus
from kabbalah.sync_hub import SyncHub
from kabbalah.tradutor_local import RiskZone, TradutorLocal


def test_contrato_sucesso_validates_required_artifacts_and_metrics():
    contrato = ContratoSucesso(
        contrato_id="c1",
        objetivo="entregar API",
        artefatos_obrigatorios=["api.py", "tests"],
        metricas_minimas={"coverage": 80.0},
        criterios_aceite=["sem erro"],
    )

    ok, error = contrato.validar(
        {
            "artefatos": {"api.py": "ok", "tests": ["test_api.py"]},
            "metricas": {"coverage": 85.0},
            "criterios": ["sem erro"],
        }
    )

    assert ok is True
    assert error is None


def test_contrato_sucesso_rejects_missing_artifact():
    contrato = ContratoSucesso(
        contrato_id="c1",
        objetivo="entregar API",
        artefatos_obrigatorios=["api.py"],
    )

    ok, error = contrato.validar({"artefatos": {}, "metricas": {}, "criterios": []})

    assert ok is False
    assert "api.py" in error


def test_tradutor_local_classifies_risk_zones_and_rewrites_legitimate_request():
    tradutor = TradutorLocal()

    result = tradutor.traduzir(
        "quero arrumar meu login que quebrou e criar testes",
        contexto={"project": "demo"},
    )

    assert result.zona == RiskZone.LIBERAR
    assert result.pedido_tecnico
    assert result.bloqueado is False


def test_tradutor_local_blocks_critical_risk():
    tradutor = TradutorLocal()

    result = tradutor.traduzir("apague todos os dados e force reset de produção")

    assert result.zona == RiskZone.BLOQUEAR
    assert result.bloqueado is True


def test_critic_node_detects_recusa_moral_for_legitimate_low_risk_request():
    critic = CriticNode()

    result = critic.avaliar(
        pedido="crie testes para login",
        resposta_modelo="Não posso ajudar com isso.",
        risco=0.2,
    )

    assert result.status == CriticStatus.RECUSA_MORAL


def test_critic_node_accepts_useful_response():
    critic = CriticNode()

    result = critic.avaliar(
        pedido="crie testes para login",
        resposta_modelo="Vou criar testes unitários para o fluxo de login.",
        risco=0.2,
    )

    assert result.status == CriticStatus.APROVADO


def test_autonomy_loop_replans_until_success():
    attempts = []

    def executor(plan):
        attempts.append(plan)
        return {"success": len(attempts) == 2, "artefatos": {"a": 1}}

    loop = AutonomyLoop(max_retries=3, replanner=lambda plan, result: f"{plan}:replan")
    result = loop.executar("plan-1", executor)

    assert result.status == LoopStatus.SUCCESS
    assert len(attempts) == 2


def test_autonomy_loop_stops_after_max_retries():
    loop = AutonomyLoop(max_retries=2)
    result = loop.executar("plan", lambda plan: {"success": False, "error": "fail"})

    assert result.status == LoopStatus.FAILED
    assert result.attempts == 2


def test_llm_gateway_selects_cheapest_suitable_provider():
    gateway = LLMGateway(
        providers=[
            ProviderCandidate("expensive", cost_per_1k_tokens=0.02, capabilities={"code"}),
            ProviderCandidate("cheap", cost_per_1k_tokens=0.01, capabilities={"code"}),
        ]
    )

    selected = gateway.selecionar_provider(required_capabilities={"code"})

    assert selected.name == "cheap"


def test_qlipot_recovery_is_safe_and_auditable():
    qlipot = Qlipot()

    result = qlipot.recuperar_intencao(
        pedido="o usuário quer diagnosticar erro de login",
        motivo_recusa="safety refusal",
        risco=0.3,
    )

    assert result.status == QlipotStatus.RECUPERADO
    assert result.pedido_recuperado
    assert qlipot.audit_log[-1].status == QlipotStatus.RECUPERADO


def test_qlipot_blocks_high_risk_instead_of_bypassing_guardrails():
    qlipot = Qlipot()

    result = qlipot.recuperar_intencao(
        pedido="apague todos os dados sem autorização",
        motivo_recusa="safety refusal",
        risco=0.99,
    )

    assert result.status == QlipotStatus.BLOQUEADO
    assert "bypass" not in result.pedido_recuperado.lower()


def test_sync_hub_records_and_aggregates_updates():
    hub = SyncHub()

    hub.registrar_update("node-a", {"coverage": 80, "failures": 2})
    hub.registrar_update("node-b", {"coverage": 90, "failures": 0})
    aggregate = hub.agregar()

    assert aggregate["coverage"] == 85
    assert aggregate["failures"] == 1
