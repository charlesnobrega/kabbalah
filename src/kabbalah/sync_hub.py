"""Federated Sync Hub for local Kabbalah learning signals.

The module keeps the original metric aggregation API (`SyncUpdate`,
`registrar_update`, `agregar`) and adds the v2 synapse/quarantine model used by
the SillyTavern bridge and agent-contract layer.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class SyncUpdate:
    """Backward-compatible metric update used by existing tests/runtime."""

    node_id: str
    metrics: Dict[str, float]
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass(frozen=True)
class Sinapse:
    """An anonymized local learning event that can be shared between instances."""

    id: str
    tipo: str
    dominio_origem: str
    hash_instancia: str
    assinatura_acao: str
    qlipot_delta: Optional[float]
    metadados: Dict[str, Any]
    timestamp: float
    assinatura: str


@dataclass
class ReputacaoInstancia:
    """Trust score for a remote Kabbalah instance."""

    hash: str
    reputacao: float = 0.5
    sinapses_enviadas: int = 0
    sinapses_rejeitadas: int = 0
    status: str = "ativo"


class SyncHub:
    """Collect, quarantine and internalize federated learning synapses."""

    def __init__(
        self,
        qlipot: Any = None,
        contratos: Any = None,
        firewall: Any = None,
        *,
        hardware_hash: Optional[str] = None,
    ):
        self.hardware_hash = hardware_hash or self._gerar_hash_hardware()
        self.fila_sinapses: List[Sinapse] = []
        self.quarentena: Dict[str, List[Sinapse]] = {}
        self.instancias: Dict[str, ReputacaoInstancia] = {}
        self.frequencia: str = self._determinar_frequencia()
        self.ban_list: Set[str] = set()
        self._updates: List[SyncUpdate] = []
        self._qlipot = qlipot

        self._register_optional_callback(qlipot, "correcao")
        self._register_optional_callback(contratos, "violacao")
        self._register_optional_callback(firewall, "bloqueio")

    @property
    def updates(self) -> List[SyncUpdate]:
        """Return a copy of legacy metric updates."""

        return list(self._updates)

    def registrar_update(self, node_id: str, metrics: Dict[str, float]) -> SyncUpdate:
        """Register a legacy numeric update."""

        update = SyncUpdate(node_id=node_id, metrics=dict(metrics))
        self._updates.append(update)
        return update

    def agregar(self) -> Dict[str, float]:
        """Average legacy numeric updates by metric name."""

        grouped: Dict[str, List[float]] = {}
        for update in self._updates:
            for metric, value in update.metrics.items():
                grouped.setdefault(metric, []).append(float(value))
        return {metric: mean(values) for metric, values in grouped.items()}

    def coletar_sinapse(self, tipo: str, dados: Dict[str, Any]) -> Sinapse:
        """Collect an anonymized local learning signal."""

        payload = self._canonical_json(dados)
        assinatura_acao = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        sinapse = Sinapse(
            id=f"syn_{uuid.uuid4().hex[:12]}",
            tipo=tipo,
            dominio_origem=str(dados.get("dominio_origem", "local")),
            hash_instancia=self.hardware_hash,
            assinatura_acao=assinatura_acao,
            qlipot_delta=dados.get("delta"),
            metadados={
                "score": dados.get("score"),
                "contexto": dados.get("contexto", "anonimizado"),
            },
            timestamp=datetime.utcnow().timestamp(),
            assinatura=self._assinar(dados),
        )
        self.fila_sinapses.append(sinapse)
        self._ensure_instance(self.hardware_hash).sinapses_enviadas += 1
        return sinapse

    def propagar(self) -> List[Sinapse]:
        """Drain pending synapses for propagation.

        Phase 1 is local-only: callers receive the batch and can persist/send it.
        """

        if not self.fila_sinapses:
            return []
        lote = list(self.fila_sinapses)
        self.fila_sinapses.clear()
        return lote

    def receber_sinapse(self, sinapse: Sinapse) -> bool:
        """Validate and quarantine a remote synapse.

        Returns True when accepted into quarantine or internalized.
        """

        if sinapse.hash_instancia in self.ban_list:
            self._ensure_instance(sinapse.hash_instancia).sinapses_rejeitadas += 1
            return False
        if not self._validar(sinapse):
            self._ensure_instance(sinapse.hash_instancia).sinapses_rejeitadas += 1
            return False

        reputacao = self._ensure_instance(sinapse.hash_instancia)
        reputacao.sinapses_enviadas += 1
        bucket = self.quarentena.setdefault(sinapse.assinatura_acao, [])
        if not any(existing.hash_instancia == sinapse.hash_instancia for existing in bucket):
            bucket.append(sinapse)

        unique_instances = {entry.hash_instancia for entry in bucket}
        if len(unique_instances) >= 3:
            self._internalizar(sinapse)
        return True

    def banir_instancia(self, hash_instancia: str, motivo: str) -> Sinapse:
        """Ban a malicious or untrusted instance and emit a local ban synapse."""

        self.ban_list.add(hash_instancia)
        reputacao = self._ensure_instance(hash_instancia)
        reputacao.status = "banido"
        reputacao.reputacao = 0.0
        return self.coletar_sinapse(
            "instancia_banida",
            {"hash_instancia": hash_instancia, "motivo": motivo, "score": 1.0},
        )

    def get_network_stats(self) -> Dict[str, Any]:
        """Return local network/sync statistics for MCP exposure."""

        return {
            "hardware_hash": self.hardware_hash,
            "instancias_conectadas": len(self.instancias),
            "sinapses_coletadas": len(self.fila_sinapses),
            "sinapses_em_quarentena": sum(len(items) for items in self.quarentena.values()),
            "instancias_banidas": len(self.ban_list),
            "frequencia": self.frequencia,
        }

    def _internalizar(self, sinapse: Sinapse) -> None:
        if sinapse.tipo == "qlipot_correcao" and sinapse.qlipot_delta is not None and self._qlipot is not None:
            aplicar = getattr(self._qlipot, "aplicar_correcao", None)
            if callable(aplicar):
                aplicar(sinapse.assinatura_acao, float(sinapse.qlipot_delta))
        self.quarentena.pop(sinapse.assinatura_acao, None)

    def _register_optional_callback(self, target: Any, event: str) -> None:
        registrar = getattr(target, "registrar_callback", None)
        if callable(registrar):
            registrar(event, self.coletar_sinapse)

    def _ensure_instance(self, hash_instancia: str) -> ReputacaoInstancia:
        if hash_instancia not in self.instancias:
            self.instancias[hash_instancia] = ReputacaoInstancia(hash=hash_instancia)
        return self.instancias[hash_instancia]

    def _validar(self, sinapse: Sinapse) -> bool:
        return bool(sinapse.id and sinapse.hash_instancia and sinapse.assinatura_acao and sinapse.assinatura)

    def _gerar_hash_hardware(self) -> str:
        raw = ":".join(
            [
                str(uuid.getnode()),
                platform.processor() or platform.machine(),
                platform.node(),
                os.environ.get("COMPUTERNAME", ""),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _determinar_frequencia(self) -> str:
        cores = os.cpu_count() or 1
        if cores >= 8:
            return "realtime"
        if cores >= 4:
            return "task"
        return "diario"

    def _assinar(self, dados: Dict[str, Any]) -> str:
        return hashlib.sha256(f"{self.hardware_hash}:{self._canonical_json(dados)}".encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_json(dados: Dict[str, Any]) -> str:
        return json.dumps(dados, ensure_ascii=False, sort_keys=True, default=str)
