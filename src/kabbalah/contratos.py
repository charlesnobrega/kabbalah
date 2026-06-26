"""Success contracts for Kabbalah v2."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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
