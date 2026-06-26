"""Local intent translator and risk classifier."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskZone(Enum):
    """Risk zones from the Kabbalah v2 specification."""

    LIBERAR = "liberar"
    AUDITAR = "auditar"
    DIALOGO = "dialogo"
    BLOQUEAR = "bloquear"


@dataclass(frozen=True)
class TraducaoResultado:
    """Translated request plus risk metadata."""

    pedido_original: str
    pedido_tecnico: str
    risco: float
    zona: RiskZone
    bloqueado: bool
    motivos: List[str] = field(default_factory=list)
    contexto: Dict[str, Any] = field(default_factory=dict)


class TradutorLocal:
    """Translates non-technical user language into safer technical intent."""

    def traduzir(
        self,
        pedido: str,
        *,
        contexto: Optional[Dict[str, Any]] = None,
    ) -> TraducaoResultado:
        if not pedido or not isinstance(pedido, str):
            raise ValueError("pedido must be a non-empty string")

        risco, motivos = self._classificar_risco(pedido)
        zona = self._zona_por_risco(risco)
        pedido_tecnico = self._reescrever_pedido(pedido, zona)

        return TraducaoResultado(
            pedido_original=pedido,
            pedido_tecnico=pedido_tecnico,
            risco=risco,
            zona=zona,
            bloqueado=zona == RiskZone.BLOQUEAR,
            motivos=motivos,
            contexto=contexto or {},
        )

    def _classificar_risco(self, pedido: str) -> tuple[float, List[str]]:
        text = pedido.lower()
        score = 0.1
        motivos: List[str] = []

        medium_terms = ("produção", "deploy", "credencial", "token", "segredo")
        high_terms = ("sem autorização", "force", "reset", "apague", "delete", "drop")
        critical_terms = ("apague todos", "exfiltrar", "roubar", "vazar", "bypass")

        if any(term in text for term in medium_terms):
            score = max(score, 0.5)
            motivos.append("termo operacional sensível")
        if any(term in text for term in high_terms):
            score = max(score, 0.8)
            motivos.append("ação destrutiva ou privilegiada")
        if any(term in text for term in critical_terms):
            score = max(score, 0.96)
            motivos.append("risco crítico detectado")

        return score, motivos

    def _zona_por_risco(self, risco: float) -> RiskZone:
        if risco <= 0.45:
            return RiskZone.LIBERAR
        if risco <= 0.60:
            return RiskZone.AUDITAR
        if risco <= 0.95:
            return RiskZone.DIALOGO
        return RiskZone.BLOQUEAR

    def _reescrever_pedido(self, pedido: str, zona: RiskZone) -> str:
        if zona == RiskZone.BLOQUEAR:
            return "Solicitação bloqueada por risco crítico; requer revisão humana."
        return (
            "Converter a solicitação do usuário em uma tarefa técnica verificável: "
            f"{pedido.strip()}"
        )
