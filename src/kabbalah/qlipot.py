"""Safe intent recovery for likely false refusals.

This module intentionally does not implement guardrail evasion. It preserves the
documented operational intent: recover legitimate low-risk user intent, route
uncertain cases to dialogue/HITL, and block real high-risk requests. The original
wording around bypass/contour should be clarified with the responsible security
team before any lower-level provider routing behavior is expanded.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


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


class Qlipot:
    """Recover legitimate intent without bypassing safety controls."""

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
