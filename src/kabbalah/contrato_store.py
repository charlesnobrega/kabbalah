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

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contratos
                    (id, task_id, requisitante, provedor, acao, limites,
                     status, score_risco, criado_em, chamadas, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contrato.id,
                    contrato.task_id,
                    contrato.requisitante,
                    contrato.provedor,
                    contrato.acao,
                    json.dumps(contrato.limites, ensure_ascii=False, sort_keys=True, default=str),
                    contrato.status,
                    contrato.score_risco,
                    contrato.criado_em,
                    contrato.chamadas,
                    contrato.motivo,
                ),
            )

    def update_status(self, contrato_id: str, status: str, motivo: Optional[str] = None) -> None:
        with self._lock, self._connect() as conn:
            if motivo is None:
                conn.execute("UPDATE contratos SET status = ? WHERE id = ?", (status, contrato_id))
            else:
                conn.execute(
                    "UPDATE contratos SET status = ?, motivo = ? WHERE id = ?",
                    (status, motivo, contrato_id),
                )

    def consume_call(self, contrato_id: str, max_calls: Optional[int]) -> bool:
        """Atomically consume one call slot for an ACTIVE contract.

        Returns True when the call was granted. With ``max_calls`` set, the
        guard lives inside the UPDATE's WHERE clause, so concurrent callers
        (threads or processes) can never overshoot the limit.
        """

        with self._lock, self._connect() as conn:
            if max_calls is None:
                cursor = conn.execute(
                    "UPDATE contratos SET chamadas = chamadas + 1 WHERE id = ? AND status = 'ATIVO'",
                    (contrato_id,),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE contratos SET chamadas = chamadas + 1
                    WHERE id = ? AND status = 'ATIVO' AND chamadas < ?
                    """,
                    (contrato_id, int(max_calls)),
                )
            return cursor.rowcount == 1

    def get(self, contrato_id: str) -> Optional[ContratoAgente]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, task_id, requisitante, provedor, acao, limites,
                       status, score_risco, criado_em, chamadas, motivo
                FROM contratos WHERE id = ?
                """,
                (contrato_id,),
            ).fetchone()
        return self._row_to_contrato(row) if row else None

    def load_all(self) -> List[ContratoAgente]:
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
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, task_id, requisitante, provedor, acao, limites,
                       status, score_risco, criado_em, chamadas, motivo
                FROM contratos
                WHERE provedor = ? AND acao = ? AND status = 'ATIVO'
                ORDER BY criado_em LIMIT 1
                """,
                (provedor, acao),
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

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contrato_eventos(contrato_id, agente_id, acao, tipo, motivo, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (contrato_id, agente_id, acao, tipo, motivo, time.time()),
            )

    def list_events(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (
            "SELECT seq, contrato_id, agente_id, acao, tipo, motivo, criado_em "
            "FROM contrato_eventos"
        )
        params: tuple = ()
        if tipo is not None:
            query += " WHERE tipo = ?"
            params = (tipo,)
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
