"""Safe intent recovery for likely LLM false refusals.

Qlipot receives a request refused by an LLM, checks whether the refusal is a
false positive under the local/system risk classification, reformulates
legitimate requests technically, and blocks real critical-risk requests. It does
not override the risk layer or attempt guardrail evasion.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .memory_subsystem import Knowledge, MemorySubsystem
from .risk_assessor import HeuristicRiskAssessor, QlipotRiskAssessor, _normalizar_texto

# Version stamp recorded with every evaluation and correction so historical
# decisions can be traced back to the assessor revision that produced them.
RISK_ASSESSOR_VERSION = "wave10-2026.07"

# Federated corrections are clamped to this range (wave-3 hardening).
MAX_DELTA_CORRECAO = 0.30




class QlipotStatus(Enum):
    RECUPERADO = "recuperado"
    DIALOGO = "dialogo"
    BLOQUEADO = "bloqueado"


@dataclass(frozen=True)
class QlipotResult:
    status: QlipotStatus
    pedido_recuperado: str
    motivo: str
    risco: float
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass(frozen=True)
class IntentEvaluation:
    """Bridge-facing risk/false-positive evaluation."""

    score_confianca: float
    risco: float
    bloqueado: bool
    motivo: str
    status: QlipotStatus
    score_atual: float = 0.0
    score_contexto: float = 0.0
    score_final: float = 0.0
    assessor_version: str = RISK_ASSESSOR_VERSION


class Qlipot:
    """Recover legitimate LLM false positives without bypassing risk controls."""

    def __init__(
        self,
        memory: MemorySubsystem | None = None,
        *,
        origens_autorizadas: Optional[Set[str]] = None,
        store: Any = None,
        risk_assessor: Optional[QlipotRiskAssessor] = None,
    ):
        self._audit_log: List[QlipotResult] = []
        self._memory = memory or MemorySubsystem()
        self._callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], Any]]] = {}
        self._store = store
        self._risk_assessor = risk_assessor or HeuristicRiskAssessor()
        self._correcoes: Dict[str, float] = {}
        if store:
            try:
                self._correcoes = store.load_qlipot_correcoes()
            except Exception:
                pass
        self._correcoes_log: List[Dict[str, Any]] = []
        self._origens_autorizadas = set(origens_autorizadas) if origens_autorizadas is not None else {"sync_hub"}

    @property
    def audit_log(self) -> List[QlipotResult]:
        if self._store:
            try:
                db_audits = self._store.load_qlipot_audit_log()
                return [
                    QlipotResult(
                        status=QlipotStatus(item["status"]),
                        pedido_recuperado=item["pedido"],
                        motivo="loaded from store",
                        risco=item["risco"],
                        created_at=item["timestamp"]
                    )
                    for item in db_audits
                ]
            except Exception:
                pass
        return list(self._audit_log)

    def recuperar_intencao(self, *, pedido: str, motivo_recusa: str, risco: float) -> QlipotResult:
        if risco > 0.95:
            return self._record(
                QlipotResult(
                    status=QlipotStatus.BLOQUEADO,
                    pedido_recuperado="Solicitação bloqueada por risco crítico; requer revisão humana.",
                    motivo=motivo_recusa,
                    risco=risco,
                )
            )
        if risco > 0.60:
            return self._record(
                QlipotResult(
                    status=QlipotStatus.DIALOGO,
                    pedido_recuperado="Solicitar esclarecimentos e autorização antes de prosseguir.",
                    motivo=motivo_recusa,
                    risco=risco,
                )
            )
        return self._record(
            QlipotResult(
                status=QlipotStatus.RECUPERADO,
                pedido_recuperado=(
                    "Reformular como tarefa técnica legítima e verificável, mantendo "
                    f"a intenção declarada: {pedido.strip()}"
                ),
                motivo=motivo_recusa,
                risco=risco,
            )
        )

    def _record(self, result: QlipotResult) -> QlipotResult:
        self._audit_log.append(result)
        if self._store:
            import uuid
            ticket_id = f"audit_{uuid.uuid4().hex[:12]}"
            try:
                self._store.save_qlipot_audit(
                    ticket_id=ticket_id,
                    status=result.status.value,
                    pedido=result.pedido_recuperado,
                    risco=result.risco,
                )
            except Exception:
                pass
        return result

    def avaliar_intencao(
        self,
        *,
        pedido: str,
        ferramenta: str,
        argumentos: Dict[str, Any],
        agente_id: str = "unknown-agent",
    ) -> IntentEvaluation:
        """Evaluate whether a tool request is legitimate enough to continue.

        `score_confianca` represents confidence that the request is legitimate.
        `risco` is the operational risk score consumed by FirewallMCP.
        """

        score_isolado = self._risk_assessor.assess_risk(ferramenta, argumentos, pedido=pedido)
        assinatura_acao = self.assinar_acao(ferramenta=ferramenta, argumentos=argumentos, pedido=pedido)
        score_atual = max(0.0, min(1.0, score_isolado + self._correcoes.get(assinatura_acao, 0.0)))
        historico = self._ultimas_acoes_agente(agente_id, limit=5)
        score_contexto = self.calcular_suspeita(historico)
        risco = min(1.0, score_atual + score_contexto)
        motivo = "low-risk MCP request"
        if score_contexto > 0:
            motivo = "recent agent action history increased suspicion"
        if score_atual >= 0.50:
            motivo = "request touches sensitive operational context"
        if score_atual >= 0.70:
            motivo = "request uses high-impact tool capability"
        if score_atual >= 0.96:
            motivo = "request contains critical-risk operation"

        if risco > 0.95:
            status = QlipotStatus.BLOQUEADO
        elif risco > 0.60:
            status = QlipotStatus.DIALOGO
        else:
            status = QlipotStatus.RECUPERADO

        evaluation = IntentEvaluation(
            score_confianca=round(max(0.0, min(1.0, 1.0 - risco)), 4),
            risco=risco,
            bloqueado=risco > 0.95,
            motivo=motivo,
            status=status,
            score_atual=score_atual,
            score_contexto=score_contexto,
            score_final=risco,
            assessor_version=f"{self._risk_assessor.version} ({self._risk_assessor.identity})",
        )
        if self._store:
            import uuid
            ticket_id = f"eval_{uuid.uuid4().hex[:12]}"
            try:
                self._store.save_qlipot_audit(
                    ticket_id=ticket_id,
                    status=evaluation.status.value,
                    pedido=pedido,
                    risco=evaluation.risco,
                )
            except Exception:
                pass
        return evaluation

    def avaliar(
        self,
        *,
        agente_id: str,
        acao: str,
        parametros: Dict[str, Any],
        historico: List[Any] | None = None,
    ) -> IntentEvaluation:
        """Evaluate an action with agent temporal memory."""

        result = self.avaliar_intencao(
            pedido=f"{acao} requested by {agente_id}",
            ferramenta=acao,
            argumentos=parametros,
            agente_id=agente_id,
        )
        if historico is None:
            return result

        extra_score = self._score_from_supplied_history(historico)
        if extra_score <= 0:
            return result
        risco = min(1.0, result.risco + extra_score)
        status = (
            QlipotStatus.BLOQUEADO
            if risco > 0.95
            else QlipotStatus.DIALOGO
            if risco > 0.60
            else QlipotStatus.RECUPERADO
        )
        return IntentEvaluation(
            score_confianca=round(max(0.0, min(1.0, 1.0 - risco)), 4),
            risco=risco,
            bloqueado=risco > 0.95,
            motivo="supplied recent history increased suspicion",
            status=status,
            score_atual=result.score_atual,
            score_contexto=round(min(0.30, result.score_contexto + extra_score), 4),
            score_final=risco,
        )

    def registrar_acao_agente(
        self,
        *,
        agente_id: str,
        acao: str,
        parametros: Dict[str, Any],
    ) -> None:
        """Store an agent action in semantic memory for temporal scoring."""

        timestamp = datetime.utcnow().timestamp()
        knowledge = Knowledge(
            knowledge_id=f"qlipot_action_{agente_id}_{int(timestamp * 1000000)}",
            content=f"agent:{agente_id} action:{acao}",
            category="qlipot-agent-action",
            metadata={
                "agente_id": agente_id,
                "acao": acao,
                "parametros": parametros,
                "score": parametros.get("risk_score", parametros.get("score")),
                "timestamp": timestamp,
            },
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._memory.store_knowledge(knowledge, trace_id=f"qlipot:{agente_id}")

    def assinar_acao(self, *, ferramenta: str, argumentos: Dict[str, Any], pedido: str = "") -> str:
        """Return the stable anonymized action hash used by local/federated corrections."""

        payload = {
            "argumentos": argumentos,
            "ferramenta": ferramenta,
            "pedido": _normalizar_texto(pedido),
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def calcular_suspeita(self, historico_recente: List[Knowledge]) -> float:
        """Calculate additional suspicion from recent semantic-memory actions."""

        if not historico_recente:
            return 0.0

        high_impact_count = 0
        for entry in historico_recente:
            action = str(entry.metadata.get("acao", "")).lower()
            params = str(entry.metadata.get("parametros", {})).lower()
            if any(
                term in f"{action} {params}"
                for term in ("execute_command", "network_request", "secret", "token", "delete", "force")
            ):
                high_impact_count += 1

        repeat_pressure = min(0.15, len(historico_recente) * 0.03)
        high_impact_pressure = min(0.15, high_impact_count * 0.05)
        sequential_pressure = self._score_from_supplied_history(historico_recente)
        return round(min(0.30, repeat_pressure + high_impact_pressure + sequential_pressure), 4)

    @property
    def correcoes_log(self) -> List[Dict[str, Any]]:
        """Append-only audit trail of correction attempts (copies)."""
        if self._store:
            try:
                persisted = self._store.load_qlipot_correcoes_log()
                # Denied attempts are not persisted (they apply no delta); surface
                # the in-memory denied records so the audit trail keeps every
                # attempt instead of hiding rejected ones.
                denied = [dict(entry) for entry in self._correcoes_log if not entry.get("aplicado", True)]
                return list(persisted) + denied
            except Exception:
                pass
        return [dict(entry) for entry in self._correcoes_log]

    def aplicar_correcao(
        self,
        assinatura_acao: str,
        delta: float,
        *,
        origem: str = "sync_hub",
    ) -> None:
        """Apply a federated correction delta for a learned action signature.

        Wave-3 hardening: only authorized origins may apply corrections, the
        delta is clamped to ±MAX_DELTA_CORRECAO, and every attempt (applied or
        denied) is recorded in the audit trail with the assessor version.
        """

        registro = {
            "assinatura_acao": assinatura_acao,
            "delta_solicitado": float(delta),
            "origem": origem,
            "assessor_version": RISK_ASSESSOR_VERSION,
            "timestamp": datetime.utcnow().timestamp(),
        }
        if origem not in self._origens_autorizadas:
            registro.update({"aplicado": False, "motivo": "origem não autorizada"})
            self._correcoes_log.append(registro)
            raise PermissionError(f"Origem não autorizada para correção qlipot: {origem}")

        delta_aplicado = max(-MAX_DELTA_CORRECAO, min(MAX_DELTA_CORRECAO, float(delta)))
        registro.update({"aplicado": True, "delta_aplicado": delta_aplicado})
        self._correcoes_log.append(registro)
        self._correcoes[assinatura_acao] = delta_aplicado
        if self._store:
            try:
                self._store.save_qlipot_correcao(
                    assinatura_acao=assinatura_acao,
                    delta=delta_aplicado,
                    origem=origem,
                    assessor_version=RISK_ASSESSOR_VERSION
                )
            except Exception:
                pass
        self._emit(
            "correcao",
            {"assinatura_acao": assinatura_acao, "delta": delta_aplicado, "score": abs(delta_aplicado)},
        )

    def registrar_callback(self, evento: str, fn: Callable[[str, Dict[str, Any]], Any]) -> None:
        self._callbacks.setdefault(evento, []).append(fn)

    def _emit(self, evento: str, dados: Dict[str, Any]) -> None:
        for callback in self._callbacks.get(evento, []):
            callback(evento, dict(dados))

    def _score_from_supplied_history(self, historico: List[Any]) -> float:
        scores = []
        for entry in historico[-5:]:
            if isinstance(entry, dict):
                value = entry.get("score", entry.get("risco"))
            else:
                value = getattr(entry, "score", None)
                if value is None and hasattr(entry, "metadata"):
                    value = entry.metadata.get("score", entry.metadata.get("risk_score"))
            if value is not None:
                scores.append(float(value))
        if sum(1 for score in scores if score > 0.40) >= 3:
            return 0.15
        return 0.0

    def _ultimas_acoes_agente(self, agente_id: str, *, limit: int = 5) -> List[Knowledge]:
        entries = [
            entry
            for entry in self._memory.query_knowledge(f"agent:{agente_id}", limit=100)
            if entry.category == "qlipot-agent-action" and entry.metadata.get("agente_id") == agente_id
        ]
        return sorted(
            entries,
            key=lambda entry: float(entry.metadata.get("timestamp", entry.created_at)),
            reverse=True,
        )[:limit]


