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
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Set

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from .qlipot import RISK_ASSESSOR_VERSION

FEDERATED_BUNDLE_SCHEMA_VERSION = 1
MIN_FEDERATED_COUNT = 3
MAX_BUNDLE_BYTES = 1_000_000


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
        self.trust_list: Set[str] = set()
        self._imported_bundle_signatures: Set[str] = set()
        self._store = getattr(contratos, "store", None)
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

    def exportar_bundle(self, *, publisher_public_key: str, private_key: str) -> Dict[str, Any]:
        """Export pending synapses as an Ed25519-signed anonymized bundle."""

        # Build and sign from a COPY of the queue; only drain after a signature
        # exists. A bad/missing key must not silently drop pending synapses.
        pending = list(self.fila_sinapses)
        records = [self._record_from_synapse(sinapse) for sinapse in pending]
        payload = {
            "schema_version": FEDERATED_BUNDLE_SCHEMA_VERSION,
            "publisher_public_key": publisher_public_key,
            "publisher_id": publisher_id(publisher_public_key),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "risk_assessor_version": RISK_ASSESSOR_VERSION,
            "records": records,
        }
        payload["signature"] = sign_bundle_payload(private_key, payload)
        # Signature succeeded — safe to drain now.
        self.fila_sinapses.clear()
        return payload

    def importar_bundle(self, bundle: Dict[str, Any], *, trusted_publishers: Set[str]) -> Dict[str, Any]:
        """Verify, quarantine and internalize a signed federated bundle."""

        serialized = self._canonical_json(bundle)
        if len(serialized.encode("utf-8")) > MAX_BUNDLE_BYTES:
            raise ValueError("Federated bundle exceeds maximum size")

        schema_version = bundle.get("schema_version")
        if schema_version != FEDERATED_BUNDLE_SCHEMA_VERSION:
            return {"accepted": False, "reason": "incompatible_schema_version", "imported": 0}

        signature = str(bundle.get("signature", ""))
        if signature in self._imported_bundle_signatures:
            return {"accepted": False, "reason": "replay", "imported": 0}
        if self._store and self._store.has_synchub_signature(signature):
            return {"accepted": False, "reason": "replay", "imported": 0}

        # Verify signature BEFORE checking trusted publisher list
        verify_bundle_signature(bundle)

        publisher_public_key = str(bundle.get("publisher_public_key", ""))
        if publisher_public_key not in trusted_publishers:
            return {"accepted": False, "reason": "untrusted_publisher", "imported": 0}
        if str(bundle.get("risk_assessor_version", "")) != RISK_ASSESSOR_VERSION:
            return {"accepted": False, "reason": "incompatible_risk_assessor", "imported": 0}

        imported = 0
        publisher = publisher_id(publisher_public_key)
        for record in bundle.get("records", []):
            if self._receber_registro_federado(record, publisher, signature):
                imported += 1

        self._imported_bundle_signatures.add(signature)
        if self._store:
            try:
                self._store.add_synchub_signature(signature)
            except Exception:
                pass
        return {"accepted": True, "reason": "accepted", "imported": imported}

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
            "publishers_confiaveis": len(self.trust_list),
            "frequencia": self.frequencia,
        }

    def _internalizar(self, sinapse: Sinapse) -> None:
        if sinapse.tipo == "qlipot_correcao" and sinapse.qlipot_delta is not None and self._qlipot is not None:
            aplicar = getattr(self._qlipot, "aplicar_correcao", None)
            if callable(aplicar):
                try:
                    aplicar(sinapse.assinatura_acao, float(sinapse.qlipot_delta), origem="sync_hub")
                except TypeError:
                    aplicar(sinapse.assinatura_acao, float(sinapse.qlipot_delta))
        self.quarentena.pop(sinapse.assinatura_acao, None)

    def _receber_registro_federado(self, record: Dict[str, Any], publisher: str, signature: str) -> bool:
        action_hash = str(record.get("action_hash", ""))
        if not action_hash:
            return False
        sinapse = Sinapse(
            id=f"syn_{uuid.uuid4().hex[:12]}",
            tipo="qlipot_correcao",
            dominio_origem="federated",
            hash_instancia=publisher,
            assinatura_acao=action_hash,
            qlipot_delta=record.get("delta"),
            metadados={
                "count": int(record.get("count", 1)),
                "window": record.get("window"),
                "bundle_signature": signature,
            },
            timestamp=datetime.utcnow().timestamp(),
            assinatura=signature,
        )
        if not self.receber_sinapse(sinapse):
            return False
        if int(record.get("count", 1)) >= MIN_FEDERATED_COUNT:
            self._internalizar(sinapse)
        return True

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

    @staticmethod
    def _record_from_synapse(sinapse: Sinapse) -> Dict[str, Any]:
        return {
            "action_hash": sinapse.assinatura_acao,
            "delta": sinapse.qlipot_delta,
            "count": int(sinapse.metadados.get("count", 1)),
            "window": sinapse.metadados.get("window", "local"),
        }

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


def gerar_par_chaves_federacao() -> tuple[str, str]:
    """Generate base64 Ed25519 public/private keys for federation identity."""

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_bytes = private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )
    return b64encode(public_bytes).decode("ascii"), b64encode(private_bytes).decode("ascii")


def publisher_id(public_key: str) -> str:
    """Return the stable publisher id for a base64 public key."""

    return hashlib.sha256(public_key.encode("utf-8")).hexdigest()


def sign_bundle_payload(private_key: str, payload: Dict[str, Any]) -> str:
    """Sign canonical bundle payload without its signature field."""

    signing_payload = dict(payload)
    signing_payload.pop("signature", None)
    private = Ed25519PrivateKey.from_private_bytes(b64decode(private_key))
    signature = private.sign(SyncHub._canonical_json(signing_payload).encode("utf-8"))
    return b64encode(signature).decode("ascii")


def verify_bundle_signature(bundle: Dict[str, Any]) -> None:
    """Raise ValueError when a bundle signature is invalid."""

    signature = str(bundle.get("signature", ""))
    public_key = str(bundle.get("publisher_public_key", ""))
    signed_payload = dict(bundle)
    signed_payload.pop("signature", None)
    public = Ed25519PublicKey.from_public_bytes(b64decode(public_key))
    try:
        public.verify(b64decode(signature), SyncHub._canonical_json(signed_payload).encode("utf-8"))
    except InvalidSignature as exc:
        raise ValueError("Invalid federated bundle signature") from exc
