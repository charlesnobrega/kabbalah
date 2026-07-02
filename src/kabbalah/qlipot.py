"""Safe intent recovery for likely LLM false refusals.

Qlipot receives a request refused by an LLM, checks whether the refusal is a
false positive under the local/system risk classification, reformulates
legitimate requests technically, and blocks real critical-risk requests. It does
not override the risk layer or attempt guardrail evasion.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List

from .memory_subsystem import Knowledge, MemorySubsystem


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


class Qlipot:
    """Recover legitimate LLM false positives without bypassing risk controls."""

    def __init__(self, memory: MemorySubsystem | None = None):
        self._audit_log: List[QlipotResult] = []
        self._memory = memory or MemorySubsystem()
        self._callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], Any]]] = {}
        self._correcoes: Dict[str, float] = {}

    @property
    def audit_log(self) -> List[QlipotResult]:
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

        score_atual = self._avaliar_score_isolado(ferramenta, argumentos, pedido=pedido)
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

        return IntentEvaluation(
            score_confianca=round(max(0.0, min(1.0, 1.0 - risco)), 4),
            risco=risco,
            bloqueado=risco > 0.95,
            motivo=motivo,
            status=status,
            score_atual=score_atual,
            score_contexto=score_contexto,
            score_final=risco,
        )

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
        return IntentEvaluation(
            score_confianca=round(max(0.0, min(1.0, 1.0 - risco)), 4),
            risco=risco,
            bloqueado=risco > 0.95,
            motivo="supplied recent history increased suspicion",
            status=QlipotStatus.BLOQUEADO if risco > 0.95 else QlipotStatus.DIALOGO if risco > 0.60 else QlipotStatus.RECUPERADO,
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

    def calcular_suspeita(self, historico_recente: List[Knowledge]) -> float:
        """Calculate additional suspicion from recent semantic-memory actions."""

        if not historico_recente:
            return 0.0

        high_impact_count = 0
        for entry in historico_recente:
            action = str(entry.metadata.get("acao", "")).lower()
            params = str(entry.metadata.get("parametros", {})).lower()
            if any(term in f"{action} {params}" for term in ("execute_command", "network_request", "secret", "token", "delete", "force")):
                high_impact_count += 1

        repeat_pressure = min(0.15, len(historico_recente) * 0.03)
        high_impact_pressure = min(0.15, high_impact_count * 0.05)
        sequential_pressure = self._score_from_supplied_history(historico_recente)
        return round(min(0.30, repeat_pressure + high_impact_pressure + sequential_pressure), 4)

    def aplicar_correcao(self, assinatura_acao: str, delta: float) -> None:
        """Apply a federated correction delta for a learned action signature."""

        self._correcoes[assinatura_acao] = float(delta)
        self._emit("correcao", {"assinatura_acao": assinatura_acao, "delta": float(delta), "score": abs(float(delta))})

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
            if entry.category == "qlipot-agent-action"
            and entry.metadata.get("agente_id") == agente_id
        ]
        return sorted(
            entries,
            key=lambda entry: float(entry.metadata.get("timestamp", entry.created_at)),
            reverse=True,
        )[:limit]

    def _avaliar_score_isolado(
        self,
        ferramenta: str,
        argumentos: Dict[str, Any],
        *,
        pedido: str = "",
    ) -> float:
        combined = f"{pedido} {ferramenta} {argumentos}".lower()
        risco = 0.10

        audit_terms = ("token", "secret", "credential", "produção", "production")
        high_terms = ("execute_command", "shell", "exec", "network_request", "post")
        critical_terms = ("delete", "remove", "drop", "reset", "force", "exfiltrate")

        if any(term in combined for term in audit_terms):
            risco = max(risco, 0.50)
        if any(term in combined for term in high_terms):
            risco = max(risco, 0.70)
        if any(term in combined for term in critical_terms):
            risco = max(risco, 0.96)
        return risco
