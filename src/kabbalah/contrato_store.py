"""SQLite persistence for agent contracts (hardening wave 2).

`ContratoStore` is the durable backing for `kabbalah.contratos.Contratos`:

* Contracts survive process restarts in every lifecycle status
  (PROPOSTO, ATIVO, CONCLUIDO, VIOLADO, REVOGADO, REJEITADO).
* `(provedor, acao, status)` is indexed for active-contract lookups.
* `max_calls` consumption is a single atomic SQL update, safe across
  threads and across processes sharing the same database file.
* Violations and contract-absence occurrences are persisted in an
  append-only event log — the store exposes no update or delete for it.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kabbalah.contratos import ContratoAgente

EVENTO_VIOLACAO = "violacao"
EVENTO_AUSENCIA_CONTRATO = "ausencia_contrato"


def sanitize_key(value: str) -> str:
    """Sanitize strings against ASCII control characters, zero-width spaces, and log injection."""
    if not isinstance(value, str):
        return value
    import unicodedata
    import re
    # Replace standard spacing control characters with spaces
    cleaned = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Then filter out other control/format/invisible characters
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) not in {"Cc", "Cf", "Cs", "Co", "Cn"})
    return cleaned.strip()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS contratos (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    requisitante TEXT NOT NULL,
    provedor TEXT NOT NULL,
    acao TEXT NOT NULL,
    limites TEXT NOT NULL,
    status TEXT NOT NULL,
    score_risco REAL NOT NULL,
    criado_em REAL NOT NULL,
    chamadas INTEGER NOT NULL DEFAULT 0,
    motivo TEXT
);
CREATE INDEX IF NOT EXISTS idx_contratos_provedor_acao_status
    ON contratos(provedor, acao, status);
CREATE TABLE IF NOT EXISTS contrato_eventos (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    contrato_id TEXT,
    agente_id TEXT NOT NULL,
    acao TEXT NOT NULL,
    tipo TEXT NOT NULL,
    motivo TEXT NOT NULL,
    criado_em REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS qlipot_correcoes (
    assinatura_acao TEXT PRIMARY KEY,
    delta_aplicado REAL NOT NULL,
    origem TEXT NOT NULL,
    assessor_version TEXT NOT NULL,
    timestamp REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS qlipot_audit_log (
    ticket_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    pedido TEXT NOT NULL,
    risco REAL NOT NULL,
    timestamp REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS synchub_signatures (
    signature TEXT PRIMARY KEY,
    imported_at REAL NOT NULL
);
"""


class ContratoStore:
    """Thread-safe SQLite store for agent contracts and their audit trail."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    # -- contracts ---------------------------------------------------------

    def save(self, contrato: ContratoAgente) -> None:
        """Insert or fully refresh a contract row."""
        contrato_id = sanitize_key(contrato.id)
        task_id = sanitize_key(contrato.task_id)
        requisitante = sanitize_key(contrato.requisitante)
        provedor = sanitize_key(contrato.provedor)
        acao = sanitize_key(contrato.acao)
        status = sanitize_key(contrato.status)
        motivo = sanitize_key(contrato.motivo) if contrato.motivo else None

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contratos
                    (id, task_id, requisitante, provedor, acao, limites,
                     status, score_risco, criado_em, chamadas, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contrato_id,
                    task_id,
                    requisitante,
                    provedor,
                    acao,
                    json.dumps(contrato.limites, ensure_ascii=False, sort_keys=True, default=str),
                    status,
                    contrato.score_risco,
                    contrato.criado_em,
                    contrato.chamadas,
                    motivo,
                ),
            )

    def update_status(self, contrato_id: str, status: str, motivo: Optional[str] = None) -> None:
        """Update the status and optional reason for an existing contract."""
        contrato_id_s = sanitize_key(contrato_id)
        status_s = sanitize_key(status)
        motivo_s = sanitize_key(motivo) if motivo else None

        with self._lock, self._connect() as conn:
            if motivo_s is None:
                conn.execute("UPDATE contratos SET status = ? WHERE id = ?", (status_s, contrato_id_s))
            else:
                conn.execute(
                    "UPDATE contratos SET status = ?, motivo = ? WHERE id = ?",
                    (status_s, motivo_s, contrato_id_s),
                )

    def consume_call(self, contrato_id: str, max_calls: Optional[int]) -> bool:
        """Atomically consume one call slot for an ACTIVE contract.

        Returns True when the call was granted. With ``max_calls`` set, the
        guard lives inside the UPDATE's WHERE clause, so concurrent callers
        (threads or processes) can never overshoot the limit.
        """
        contrato_id_s = sanitize_key(contrato_id)

        with self._lock, self._connect() as conn:
            if max_calls is None:
                cursor = conn.execute(
                    "UPDATE contratos SET chamadas = chamadas + 1 WHERE id = ? AND status = 'ATIVO'",
                    (contrato_id_s,),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE contratos SET chamadas = chamadas + 1
                    WHERE id = ? AND status = 'ATIVO' AND chamadas < ?
                    """,
                    (contrato_id_s, int(max_calls)),
                )
            return cursor.rowcount == 1

    def get(self, contrato_id: str) -> Optional[ContratoAgente]:
        """Load one contract by ID, returning None when it is absent."""
        contrato_id_s = sanitize_key(contrato_id)

        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, task_id, requisitante, provedor, acao, limites,
                       status, score_risco, criado_em, chamadas, motivo
                FROM contratos WHERE id = ?
                """,
                (contrato_id_s,),
            ).fetchone()
        return self._row_to_contrato(row) if row else None

    def load_all(self) -> List[ContratoAgente]:
        """Load all persisted contracts ordered by creation time."""

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, task_id, requisitante, provedor, acao, limites,
                       status, score_risco, criado_em, chamadas, motivo
                FROM contratos ORDER BY criado_em
                """
            ).fetchall()
        return [self._row_to_contrato(row) for row in rows]

    def find_active(self, provedor: str, acao: str) -> Optional[ContratoAgente]:
        """Find the oldest active contract authorizing a provider/action pair."""
        provedor_s = sanitize_key(provedor)
        acao_s = sanitize_key(acao)

        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, task_id, requisitante, provedor, acao, limites,
                       status, score_risco, criado_em, chamadas, motivo
                FROM contratos
                WHERE provedor = ? AND acao = ? AND status = 'ATIVO'
                ORDER BY criado_em LIMIT 1
                """,
                (provedor_s, acao_s),
            ).fetchone()
        return self._row_to_contrato(row) if row else None

    # -- append-only audit events -----------------------------------------

    def append_event(
        self,
        *,
        tipo: str,
        agente_id: str,
        acao: str,
        motivo: str,
        contrato_id: Optional[str] = None,
    ) -> None:
        """Append one audit event. There is intentionally no update/delete."""
        tipo_s = sanitize_key(tipo)
        agente_s = sanitize_key(agente_id)
        acao_s = sanitize_key(acao)
        motivo_s = sanitize_key(motivo)
        contrato_s = sanitize_key(contrato_id) if contrato_id else None

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contrato_eventos(contrato_id, agente_id, acao, tipo, motivo, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (contrato_s, agente_s, acao_s, tipo_s, motivo_s, time.time()),
            )

    def list_events(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        """List append-only audit events, optionally filtered by event type."""
        tipo_s = sanitize_key(tipo) if tipo else None

        query = "SELECT seq, contrato_id, agente_id, acao, tipo, motivo, criado_em FROM contrato_eventos"
        params: tuple = ()
        if tipo_s is not None:
            query += " WHERE tipo = ?"
            params = (tipo_s,)
        query += " ORDER BY seq"
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "seq": row[0],
                "contrato_id": row[1],
                "agente_id": row[2],
                "acao": row[3],
                "tipo": row[4],
                "motivo": row[5],
                "criado_em": row[6],
            }
            for row in rows
        ]

    # -- qlipot and sync_hub persistence ----------------------------------

    def save_qlipot_correcao(self, assinatura_acao: str, delta: float, origem: str, assessor_version: str) -> None:
        """Save a qlipot correction permanently."""
        sig_s = sanitize_key(assinatura_acao)
        origem_s = sanitize_key(origem)
        ver_s = sanitize_key(assessor_version)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO qlipot_correcoes
                (assinatura_acao, delta_aplicado, origem, assessor_version, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sig_s, float(delta), origem_s, ver_s, time.time()),
            )

    def load_qlipot_correcoes(self) -> Dict[str, float]:
        """Load all qlipot corrections as a mapping."""
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT assinatura_acao, delta_aplicado FROM qlipot_correcoes").fetchall()
        return {row[0]: row[1] for row in rows}

    def load_qlipot_correcoes_log(self) -> List[Dict[str, Any]]:
        """Load all applied corrections logs."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT assinatura_acao, delta_aplicado, origem, assessor_version, timestamp FROM qlipot_correcoes ORDER BY timestamp"
            ).fetchall()
        return [
            {
                "assinatura_acao": row[0],
                "delta_aplicado": row[1],
                "origem": row[2],
                "assessor_version": row[3],
                "timestamp": row[4],
                "aplicado": True,
            }
            for row in rows
        ]

    def save_qlipot_audit(self, ticket_id: str, status: str, pedido: str, risco: float) -> None:
        """Save a qlipot risk evaluation to the audit log."""
        ticket_s = sanitize_key(ticket_id)
        status_s = sanitize_key(status)
        pedido_s = sanitize_key(pedido)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO qlipot_audit_log
                (ticket_id, status, pedido, risco, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticket_s, status_s, pedido_s, float(risco), time.time()),
            )

    def load_qlipot_audit_log(self) -> List[Dict[str, Any]]:
        """Load qlipot audit logs."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT ticket_id, status, pedido, risco, timestamp FROM qlipot_audit_log ORDER BY timestamp"
            ).fetchall()
        # Mock class for compatibility if needed, or dict
        return [
            {
                "ticket_id": row[0],
                "status": row[1],
                "pedido": row[2],
                "risco": row[3],
                "timestamp": row[4],
            }
            for row in rows
        ]

    def add_synchub_signature(self, signature: str) -> None:
        """Store imported bundle signature to prevent replay attacks."""
        sig_s = sanitize_key(signature)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO synchub_signatures(signature, imported_at) VALUES (?, ?)",
                (sig_s, time.time()),
            )

    def has_synchub_signature(self, signature: str) -> bool:
        """Check if bundle signature was already imported."""
        sig_s = sanitize_key(signature)
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM synchub_signatures WHERE signature = ?", (sig_s,)).fetchone()
        return row is not None

    @staticmethod
    def _row_to_contrato(row: tuple) -> ContratoAgente:
        return ContratoAgente(
            id=row[0],
            task_id=row[1],
            requisitante=row[2],
            provedor=row[3],
            acao=row[4],
            limites=json.loads(row[5]),
            status=row[6],
            score_risco=row[7],
            criado_em=row[8],
            chamadas=row[9],
            motivo=row[10],
        )
