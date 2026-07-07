"""Contracts for Kabbalah v2.

This module contains two compatible contract layers:

* `ContratoSucesso`: existing success/acceptance criteria contracts.
* `Contratos`: agent-to-agent operational contracts used by MCP authorization.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from kabbalah.contrato_store import ContratoStore


class ContractStatus:
    """Lifecycle states for agent-to-agent operational contracts."""

    PROPOSTO = "PROPOSTO"
    ATIVO = "ATIVO"
    CONCLUIDO = "CONCLUIDO"
    VIOLADO = "VIOLADO"
    REVOGADO = "REVOGADO"
    REJEITADO = "REJEITADO"


class VerificationOutcome:
    """Detailed result of a contract verification.

    Distinguishes the absence of a contract (a normal bootstrap condition)
    from real violations of an existing contract (limit or expiry).
    """

    ALLOWED = "ALLOWED"
    NO_CONTRACT = "NO_CONTRACT"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ContratoSucesso:
    """Defines measurable success criteria for an operation or task."""

    contrato_id: str
    objetivo: str
    artefatos_obrigatorios: List[str] = field(default_factory=list)
    metricas_minimas: Dict[str, float] = field(default_factory=dict)
    criterios_aceite: List[str] = field(default_factory=list)

    def validar(self, resultado: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate an execution result against this success contract."""

        artefatos = resultado.get("artefatos", {}) or {}
        metricas = resultado.get("metricas", {}) or {}
        criterios = resultado.get("criterios", []) or []

        for artefato in self.artefatos_obrigatorios:
            if artefato not in artefatos:
                return False, f"Missing required artifact: {artefato}"

        for metrica, minimo in self.metricas_minimas.items():
            valor = metricas.get(metrica)
            if valor is None:
                return False, f"Missing required metric: {metrica}"
            if float(valor) < minimo:
                return False, f"Metric '{metrica}' below minimum: {valor} < {minimo}"

        for criterio in self.criterios_aceite:
            if criterio not in criterios:
                return False, f"Acceptance criterion not satisfied: {criterio}"

        return True, None


@dataclass
class ContratoAgente:
    """Operational agreement allowing a provider agent to perform an action."""

    id: str
    task_id: str
    requisitante: str
    provedor: str
    acao: str
    limites: Dict[str, Any]
    status: str
    score_risco: float
    criado_em: float
    chamadas: int = 0
    motivo: Optional[str] = None


ContractCallback = Callable[[str, Dict[str, Any]], Any]


class Contratos:
    """Manage explicit contracts between agents before cross-agent actions.

    When ``store`` is provided, every contract mutation is written through to
    SQLite, persisted contracts are reloaded on construction (an active
    contract survives a process restart), and ``max_calls`` consumption is
    delegated to an atomic SQL update.
    """

    def __init__(
        self,
        firewall: Any = None,
        qlipot: Any = None,
        hitl: Any = None,
        memoria: Any = None,
        store: Optional["ContratoStore"] = None,
    ):
        self.firewall = firewall
        self.qlipot = qlipot
        self.hitl = hitl
        self.memoria = memoria
        self.store = store
        self._lock = threading.RLock()
        self._contratos: Dict[str, ContratoAgente] = {}
        self._callbacks: Dict[str, List[ContractCallback]] = {}
        if store is not None:
            for contrato in store.load_all():
                self._contratos[contrato.id] = contrato

    @property
    def contratos(self) -> Dict[str, ContratoAgente]:
        """Return a shallow copy of the in-memory contract index."""

        return dict(self._contratos)

    def registrar_callback(self, evento: str, fn: ContractCallback) -> None:
        """Register a callback invoked when a contract lifecycle event occurs."""

        self._callbacks.setdefault(evento, []).append(fn)

    def propor(
        self,
        requisitante: str,
        provedor: str,
        acao: str,
        limites: Dict[str, Any],
        papeis: List[str],
        *,
        task_id: Optional[str] = None,
    ) -> ContratoAgente:
        """Create a proposed contract. Only coordinator agents can propose."""

        if "coordinator" not in papeis:
            raise PermissionError("Só coordinators propõem contratos")

        score_risco = self._avaliar_risco(requisitante, acao, limites)
        contrato = ContratoAgente(
            id=f"contract_{uuid.uuid4().hex[:12]}",
            task_id=task_id or f"task_{uuid.uuid4().hex[:12]}",
            requisitante=requisitante,
            provedor=provedor,
            acao=acao,
            limites=dict(limites),
            status=ContractStatus.PROPOSTO,
            score_risco=score_risco,
            criado_em=datetime.utcnow().timestamp(),
        )
        with self._lock:
            self._contratos[contrato.id] = contrato
            self._persist(contrato)

        if score_risco > 0.60 and self.hitl is not None:
            solicitar = getattr(self.hitl, "solicitar", None)
            if callable(solicitar):
                solicitar(
                    agente_id=requisitante,
                    acao=f"propor_contrato:{acao}",
                    risco=score_risco,
                    contexto={"contrato_id": contrato.id, "provedor": provedor, "limites": dict(limites)},
                    trace_id=contrato.id,
                )

        self._emit("proposta", {"contrato_id": contrato.id, "score": score_risco})
        return contrato

    def assinar(self, contrato_id: str, provedor: str) -> bool:
        """Activate a proposed contract when the expected provider signs it."""

        with self._lock:
            contrato = self._get(contrato_id)
            if contrato.provedor != provedor:
                return False
            if contrato.status != ContractStatus.PROPOSTO:
                return False
            contrato.status = ContractStatus.ATIVO
            self._persist(contrato)
        self._emit("assinado", {"contrato_id": contrato.id, "provedor": provedor})
        return True

    def rejeitar(self, contrato_id: str, provedor: str, motivo: str = "") -> bool:
        """Reject a proposed contract when the expected provider declines it."""

        with self._lock:
            contrato = self._get(contrato_id)
            if contrato.provedor != provedor:
                return False
            if contrato.status != ContractStatus.PROPOSTO:
                return False
            contrato.status = ContractStatus.REJEITADO
            contrato.motivo = motivo
            self._persist(contrato)
        self._emit("rejeitado", {"contrato_id": contrato.id, "motivo": motivo})
        return True

    def verificar(self, agente_id: str, acao: str) -> bool:
        """Check whether an active contract allows this agent/action pair."""

        return self.verificar_detalhado(agente_id, acao) == VerificationOutcome.ALLOWED

    def verificar_detalhado(self, agente_id: str, acao: str, *, consume: bool = True) -> str:
        """Verify a call, reporting a `VerificationOutcome`.

        With ``consume=True`` (default) a call slot is consumed. With
        ``consume=False`` this is a side-effect-free *peek*: it validates that
        an active contract exists and still has budget, but does not consume or
        register violations — used to gate before HITL so a pending/denied
        approval does not exhaust a `max_calls` contract.

        `NO_CONTRACT` is not a violation: nothing is escalated and no
        contract changes status. Limit and expiry failures are real
        violations of an existing active contract.
        """

        with self._lock:
            contrato = self._find_active(agente_id, acao)
            if contrato is None:
                return VerificationOutcome.NO_CONTRACT

            timeout_min = contrato.limites.get("timeout_min")
            if timeout_min is not None:
                age_seconds = datetime.utcnow().timestamp() - contrato.criado_em
                if age_seconds > float(timeout_min) * 60:
                    # Breach detection registers a violation even on peek; only
                    # the call-slot consumption (chamadas increment) is deferred.
                    self._registrar_violacao_contrato(contrato, agente_id, acao, "Contrato expirado por timeout_min")
                    return VerificationOutcome.EXPIRED

            max_calls = contrato.limites.get("max_calls")
            if not consume:
                if max_calls is not None and contrato.chamadas >= int(max_calls):
                    self._registrar_violacao_contrato(contrato, agente_id, acao, "Limite max_calls excedido")
                    return VerificationOutcome.LIMIT_EXCEEDED
                return VerificationOutcome.ALLOWED

            if self.store is not None:
                granted = self.store.consume_call(contrato.id, int(max_calls) if max_calls is not None else None)
                if not granted:
                    self._registrar_violacao_contrato(contrato, agente_id, acao, "Limite max_calls excedido")
                    return VerificationOutcome.LIMIT_EXCEEDED
                contrato.chamadas += 1
                return VerificationOutcome.ALLOWED

            if max_calls is not None and contrato.chamadas >= int(max_calls):
                self._registrar_violacao_contrato(contrato, agente_id, acao, "Limite max_calls excedido")
                return VerificationOutcome.LIMIT_EXCEEDED

            contrato.chamadas += 1
            return VerificationOutcome.ALLOWED

    def registrar_violacao(self, agente_id: str, acao: str, motivo: str) -> None:
        """Record a violation of the active contract for this agent/action.

        When no active contract exists, the occurrence is recorded as
        contract absence instead of a violation (wave-2 hardening: absence
        is a bootstrap condition, not a breach of an existing agreement).
        """

        with self._lock:
            contrato = self._find_active(agente_id, acao)
            if contrato is None:
                self.registrar_ausencia(agente_id, acao, motivo)
                return
            self._registrar_violacao_contrato(contrato, agente_id, acao, motivo)

    def registrar_ausencia(self, agente_id: str, acao: str, motivo: str) -> None:
        """Record an action attempted without any active contract."""

        if self.store is not None:
            from kabbalah.contrato_store import EVENTO_AUSENCIA_CONTRATO

            self.store.append_event(
                tipo=EVENTO_AUSENCIA_CONTRATO,
                agente_id=agente_id,
                acao=acao,
                motivo=motivo,
                contrato_id=None,
            )
        self._emit(
            "ausencia_contrato",
            {"agente_id": agente_id, "acao": acao, "motivo": motivo, "contrato_id": None},
        )

    def _registrar_violacao_contrato(self, contrato: ContratoAgente, agente_id: str, acao: str, motivo: str) -> None:
        with self._lock:
            contrato.status = ContractStatus.VIOLADO
            contrato.motivo = motivo
            if self.store is not None:
                from kabbalah.contrato_store import EVENTO_VIOLACAO

                # update_status (not save) so the atomic `chamadas` counter in
                # the database is never overwritten by an in-memory value.
                self.store.update_status(contrato.id, ContractStatus.VIOLADO, motivo)
                self.store.append_event(
                    tipo=EVENTO_VIOLACAO,
                    agente_id=agente_id,
                    acao=acao,
                    motivo=motivo,
                    contrato_id=contrato.id,
                )

        if self.hitl is not None:
            solicitar = getattr(self.hitl, "solicitar", None)
            if callable(solicitar):
                solicitar(
                    agente_id=agente_id,
                    acao=f"violacao_contrato:{acao}",
                    risco=0.95,
                    contexto={"motivo": motivo, "contrato_id": contrato.id},
                    trace_id=f"contract_violation_{uuid.uuid4().hex[:12]}",
                )

        self._emit(
            "violacao",
            {
                "agente_id": agente_id,
                "acao": acao,
                "motivo": motivo,
                "contrato_id": contrato.id,
                "score": 0.95,
            },
        )

    def complete_task(self, task_id: str, agente_id: str) -> List[ContratoAgente]:
        """Mark all active/proposed contracts for a task as completed."""

        affected = []
        with self._lock:
            for contrato in self._contratos.values():
                if contrato.task_id == task_id and contrato.status in {ContractStatus.PROPOSTO, ContractStatus.ATIVO}:
                    contrato.status = ContractStatus.CONCLUIDO
                    self._persist(contrato)
                    affected.append(contrato)
        self._emit("task_concluida", {"task_id": task_id, "agente_id": agente_id, "count": len(affected)})
        return affected

    def revogar(self, contrato_id: str, aprovado_por: str, motivo: str = "") -> bool:
        """Revoke a proposed or active contract after external approval."""

        with self._lock:
            contrato = self._get(contrato_id)
            if contrato.status not in {ContractStatus.PROPOSTO, ContractStatus.ATIVO}:
                return False
            contrato.status = ContractStatus.REVOGADO
            contrato.motivo = motivo or f"Revogado por {aprovado_por}"
            self._persist(contrato)
        self._emit("revogado", {"contrato_id": contrato.id, "aprovado_por": aprovado_por, "motivo": contrato.motivo})
        return True

    def contratos_por_task(self, task_id: str) -> List[ContratoAgente]:
        """List all contracts associated with a task identifier."""

        return [contrato for contrato in self._contratos.values() if contrato.task_id == task_id]

    def _avaliar_risco(self, requisitante: str, acao: str, limites: Dict[str, Any]) -> float:
        if self.qlipot is None:
            return 0.2
        avaliar = getattr(self.qlipot, "avaliar", None)
        if callable(avaliar):
            result = avaliar(agente_id=requisitante, acao=acao, parametros={"limites": dict(limites)})
            return float(getattr(result, "risco", result if isinstance(result, (int, float)) else 0.2))
        return 0.2

    def _find_active(self, agente_id: str, acao: str) -> Optional[ContratoAgente]:
        for contrato in self._contratos.values():
            if contrato.provedor == agente_id and contrato.acao == acao and contrato.status == ContractStatus.ATIVO:
                return contrato
        return None

    def _get(self, contrato_id: str) -> ContratoAgente:
        if contrato_id not in self._contratos:
            raise KeyError(f"Contrato não encontrado: {contrato_id}")
        return self._contratos[contrato_id]

    def _persist(self, contrato: ContratoAgente) -> None:
        if self.store is not None:
            self.store.save(contrato)

    def _emit(self, evento: str, dados: Dict[str, Any]) -> None:
        for callback in self._callbacks.get(evento, []):
            callback(evento, dict(dados))
