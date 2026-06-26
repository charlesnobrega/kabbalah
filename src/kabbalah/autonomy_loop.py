"""Autonomy loop with bounded replanning."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class LoopStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class LoopResult:
    status: LoopStatus
    attempts: int
    final_plan: Any
    result: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)


Executor = Callable[[Any], Dict[str, Any]]
Replanner = Callable[[Any, Dict[str, Any]], Any]


class AutonomyLoop:
    """Execute a plan, then replan up to max_retries if it fails."""

    def __init__(self, max_retries: int = 3, replanner: Optional[Replanner] = None):
        if max_retries <= 0:
            raise ValueError("max_retries must be positive")
        self.max_retries = max_retries
        self._replanner = replanner or self._default_replanner

    def executar(self, plano: Any, executor: Executor) -> LoopResult:
        current_plan = plano
        history: List[Dict[str, Any]] = []
        last_result: Dict[str, Any] = {}

        for attempt in range(1, self.max_retries + 1):
            last_result = executor(current_plan)
            history.append({"attempt": attempt, "plan": current_plan, "result": last_result})
            if last_result.get("success") is True:
                return LoopResult(
                    status=LoopStatus.SUCCESS,
                    attempts=attempt,
                    final_plan=current_plan,
                    result=last_result,
                    history=history,
                )
            current_plan = self._replanner(current_plan, last_result)

        return LoopResult(
            status=LoopStatus.FAILED,
            attempts=self.max_retries,
            final_plan=current_plan,
            result=last_result,
            history=history,
        )

    def _default_replanner(self, plano: Any, resultado: Dict[str, Any]) -> Any:
        if isinstance(plano, dict):
            updated = dict(plano)
            updated.setdefault("replanning_notes", []).append(resultado.get("error", "failed"))
            return updated
        return plano
