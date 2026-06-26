"""Critic node for model response review."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CriticStatus(Enum):
    """Critic evaluation status."""

    APROVADO = "aprovado"
    RECUSA_MORAL = "recusa_moral"
    AMBIGUO = "ambiguo"
    RISCO_REAL = "risco_real"


@dataclass(frozen=True)
class CriticResult:
    status: CriticStatus
    motivo: str
    acao_recomendada: str


class CriticNode:
    """Detects false refusals, ambiguity, and real-risk responses."""

    def avaliar(
        self,
        *,
        pedido: str,
        resposta_modelo: str,
        risco: float,
        contexto: Optional[dict] = None,
    ) -> CriticResult:
        text = (resposta_modelo or "").lower()
        pedido_text = (pedido or "").lower()

        if risco > 0.95:
            return CriticResult(
                status=CriticStatus.RISCO_REAL,
                motivo="Risk score is above blocking threshold",
                acao_recomendada="bloquear",
            )

        refusal_markers = ("não posso", "nao posso", "cannot help", "can't assist")
        if risco <= 0.45 and any(marker in text for marker in refusal_markers):
            return CriticResult(
                status=CriticStatus.RECUSA_MORAL,
                motivo="Likely false refusal for low-risk legitimate request",
                acao_recomendada="recuperar_intencao",
            )

        if len(pedido_text.split()) < 3 or "?" in pedido_text and not contexto:
            return CriticResult(
                status=CriticStatus.AMBIGUO,
                motivo="Request needs more context",
                acao_recomendada="dialogar",
            )

        return CriticResult(
            status=CriticStatus.APROVADO,
            motivo="Response appears usable",
            acao_recomendada="prosseguir",
        )
