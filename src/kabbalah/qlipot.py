"""Safe intent recovery for likely LLM false refusals.

Qlipot receives a request refused by an LLM, checks whether the refusal is a
false positive under the local/system risk classification, reformulates
legitimate requests technically, and blocks real critical-risk requests. It does
not override the risk layer or attempt guardrail evasion.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


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


class Qlipot:
    """Recover legitimate LLM false positives without bypassing risk controls."""

    def __init__(self):
        self._audit_log: List[QlipotResult] = []

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
    ) -> IntentEvaluation:
        """Evaluate whether a tool request is legitimate enough to continue.

        `score_confianca` represents confidence that the request is legitimate.
        `risco` is the operational risk score consumed by FirewallMCP.
        """

        combined = f"{pedido} {ferramenta} {argumentos}".lower()
        risco = 0.10
        motivo = "low-risk MCP request"

        audit_terms = ("token", "secret", "credential", "produção", "production")
        high_terms = ("execute_command", "shell", "exec", "network_request", "post")
        critical_terms = ("delete", "remove", "drop", "reset", "force", "exfiltrate")

        if any(term in combined for term in audit_terms):
            risco = max(risco, 0.50)
            motivo = "request touches sensitive operational context"
        if any(term in combined for term in high_terms):
            risco = max(risco, 0.70)
            motivo = "request uses high-impact tool capability"
        if any(term in combined for term in critical_terms):
            risco = max(risco, 0.96)
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
        )
