"""Federated update aggregation hub."""

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Dict, List


@dataclass(frozen=True)
class SyncUpdate:
    node_id: str
    metrics: Dict[str, float]
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


class SyncHub:
    """Collect and aggregate local node learning updates."""

    def __init__(self):
        self._updates: List[SyncUpdate] = []

    @property
    def updates(self) -> List[SyncUpdate]:
        return list(self._updates)

    def registrar_update(self, node_id: str, metrics: Dict[str, float]) -> SyncUpdate:
        update = SyncUpdate(node_id=node_id, metrics=dict(metrics))
        self._updates.append(update)
        return update

    def agregar(self) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = {}
        for update in self._updates:
            for metric, value in update.metrics.items():
                grouped.setdefault(metric, []).append(float(value))
        return {metric: mean(values) for metric, values in grouped.items()}
