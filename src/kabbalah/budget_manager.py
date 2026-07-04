"""Budget and consumption tracking primitives.

Wave 5 introduces only the append-only ledger. Enforcement is intentionally left
for the later Budget Manager wave.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget_ledger (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost REAL NOT NULL,
    trace_id TEXT NOT NULL,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_budget_ledger_trace_id
    ON budget_ledger(trace_id);
"""


class BudgetLedger:
    """Append-only SQLite ledger for LLM consumption records."""

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

    def record_call(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost: float,
        trace_id: str,
    ) -> None:
        """Append one consumption record."""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO budget_ledger(
                    provider, model, input_tokens, output_tokens,
                    total_tokens, cost, trace_id, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    model,
                    int(input_tokens),
                    int(output_tokens),
                    int(total_tokens),
                    float(cost),
                    trace_id,
                    time.time(),
                ),
            )

    def list_entries(self) -> List[Dict[str, Any]]:
        """List ledger entries in append order."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT seq, provider, model, input_tokens, output_tokens,
                       total_tokens, cost, trace_id, timestamp
                FROM budget_ledger
                ORDER BY seq
                """
            ).fetchall()
        return [
            {
                "seq": row[0],
                "provider": row[1],
                "model": row[2],
                "input_tokens": row[3],
                "output_tokens": row[4],
                "total_tokens": row[5],
                "cost": row[6],
                "trace_id": row[7],
                "timestamp": row[8],
            }
            for row in rows
        ]
