"""Budget and consumption tracking primitives."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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


class BudgetExceededError(RuntimeError):
    """Raised when budget enforcement is configured to block excess usage."""

    def __init__(self, decision: "BudgetDecision"):
        self.decision = decision
        scopes = ", ".join(decision.exceeded)
        super().__init__(f"Budget exceeded for {scopes}; projected_cost={decision.projected_cost:.8f}")


@dataclass(frozen=True)
class BudgetDecision:
    """Result from a budget check."""

    allowed: bool
    mode: str
    exceeded: List[str] = field(default_factory=list)
    projected_cost: float = 0.0
    current_costs: Dict[str, float] = field(default_factory=dict)


class BudgetManager:
    """Evaluate budget limits against the append-only ledger."""

    VALID_MODES = {"warn", "block"}

    def __init__(
        self,
        ledger: BudgetLedger,
        *,
        run_limit_usd: Optional[float] = None,
        branch_limit_usd: Optional[float] = None,
        daily_limit_usd: Optional[float] = None,
        provider_limits_usd: Optional[Dict[str, float]] = None,
        mode: str = "warn",
    ):
        normalized_mode = mode.lower()
        if normalized_mode not in self.VALID_MODES:
            raise ValueError("Budget mode must be 'warn' or 'block'")

        self.ledger = ledger
        self.run_limit_usd = run_limit_usd
        self.branch_limit_usd = branch_limit_usd
        self.daily_limit_usd = daily_limit_usd
        self.provider_limits_usd = {provider: float(limit) for provider, limit in (provider_limits_usd or {}).items()}
        self.mode = normalized_mode

    @classmethod
    def from_env(cls, ledger: BudgetLedger) -> "BudgetManager":
        """Create a manager from ``KABBALAH_BUDGET_*`` environment variables."""
        import os

        provider_limits: Dict[str, float] = {}
        prefix = "KABBALAH_BUDGET_PROVIDER_"
        suffix = "_USD"
        for key, value in os.environ.items():
            if key.startswith(prefix) and key.endswith(suffix):
                provider = key[len(prefix) : -len(suffix)].lower()
                provider_limits[provider] = float(value)

        return cls(
            ledger,
            run_limit_usd=_optional_float(os.getenv("KABBALAH_BUDGET_RUN_USD")),
            branch_limit_usd=_optional_float(os.getenv("KABBALAH_BUDGET_BRANCH_USD")),
            daily_limit_usd=_optional_float(os.getenv("KABBALAH_BUDGET_DAILY_USD")),
            provider_limits_usd=provider_limits,
            mode=os.getenv("KABBALAH_BUDGET_MODE", "warn"),
        )

    def enforce_call(
        self,
        *,
        provider: str,
        projected_cost: float,
        trace_id: str,
    ) -> BudgetDecision:
        """Check whether a projected call is within configured limits."""
        entries = self.ledger.list_entries()
        projected = float(projected_cost)
        run_id = _run_id_from_trace(trace_id)
        branch_id = _branch_id_from_trace(trace_id)
        provider_cost = _sum_cost(entry for entry in entries if entry["provider"] == provider)
        run_cost = _sum_cost(entry for entry in entries if _run_id_from_trace(entry["trace_id"]) == run_id)
        branch_cost = _sum_cost(entry for entry in entries if _branch_id_from_trace(entry["trace_id"]) == branch_id)
        daily_cost = _sum_cost(_entries_today(entries))

        exceeded: List[str] = []
        if self.run_limit_usd is not None and run_cost + projected > self.run_limit_usd:
            exceeded.append("run")
        if self.branch_limit_usd is not None and branch_cost + projected > self.branch_limit_usd:
            exceeded.append("branch")
        if self.daily_limit_usd is not None and daily_cost + projected > self.daily_limit_usd:
            exceeded.append("daily")
        provider_limit = self.provider_limits_usd.get(provider)
        if provider_limit is not None and provider_cost + projected > provider_limit:
            exceeded.append(f"provider:{provider}")

        decision = BudgetDecision(
            allowed=not exceeded,
            mode=self.mode,
            exceeded=exceeded,
            projected_cost=projected,
            current_costs={
                "provider": provider_cost,
                "run": run_cost,
                "branch": branch_cost,
                "daily": daily_cost,
            },
        )
        if exceeded and self.mode == "block":
            raise BudgetExceededError(decision)
        return decision

    def get_budget_stats(self) -> Dict[str, Any]:
        """Return aggregate budget and consumption stats."""
        entries = self.ledger.list_entries()
        provider_costs: Dict[str, float] = {}
        run_costs: Dict[str, float] = {}
        for entry in entries:
            provider_costs[entry["provider"]] = provider_costs.get(entry["provider"], 0.0) + float(entry["cost"])
            run_id = _run_id_from_trace(entry["trace_id"])
            run_costs[run_id] = run_costs.get(run_id, 0.0) + float(entry["cost"])

        return {
            "mode": self.mode,
            "total_cost": _sum_cost(entries),
            "daily_cost": _sum_cost(_entries_today(entries)),
            "provider_costs": provider_costs,
            "run_costs": run_costs,
            "limits": {
                "run_usd": self.run_limit_usd,
                "branch_usd": self.branch_limit_usd,
                "daily_usd": self.daily_limit_usd,
                "provider_usd": dict(self.provider_limits_usd),
            },
        }


def _optional_float(value: Optional[str]) -> Optional[float]:
    if value in (None, ""):
        return None
    return float(value)


def _sum_cost(entries: Iterable[Dict[str, Any]]) -> float:
    return sum(float(entry["cost"]) for entry in entries)


def _run_id_from_trace(trace_id: str) -> str:
    return trace_id.split(":", 1)[0]


def _branch_id_from_trace(trace_id: str) -> str:
    parts = trace_id.split(":")
    return ":".join(parts[:2]) if len(parts) > 1 else trace_id


def _entries_today(entries: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    today = time.localtime().tm_yday
    year = time.localtime().tm_year
    return [
        entry
        for entry in entries
        if time.localtime(float(entry["timestamp"])).tm_yday == today
        and time.localtime(float(entry["timestamp"])).tm_year == year
    ]
