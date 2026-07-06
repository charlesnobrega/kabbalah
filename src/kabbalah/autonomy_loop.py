"""Autonomy loop with bounded replanning and optional tree search."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .budget_manager import BudgetExceededError, BudgetManager


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
BranchGenerator = Callable[[Any, Dict[str, Any], int], List[Any]]
Scorer = Callable[[Any, Dict[str, Any]], float]
BudgetEstimator = Callable[[Any], float]


@dataclass(frozen=True)
class _SearchNode:
    node_id: str
    plan: Any
    depth: int
    score: float
    order: int
    branch_id: str
    branch_cost: float = 0.0


class AutonomyLoop:
    """Execute a plan linearly by default, or as bounded tree search."""

    VALID_SEARCH_MODES = {"linear", "tree"}

    def __init__(
        self,
        max_retries: int = 3,
        replanner: Optional[Replanner] = None,
        *,
        search_mode: str | None = None,
        branch_generator: BranchGenerator | None = None,
        scorer: Scorer | None = None,
        budget_manager: BudgetManager | None = None,
        budget_estimator: BudgetEstimator | None = None,
        branch_factor: int = 2,
        max_depth: int = 2,
        max_nodes: int | None = None,
        prune_threshold: float = 0.0,
    ):
        if max_retries <= 0:
            raise ValueError("max_retries must be positive")
        mode = (search_mode or os.getenv("KABBALAH_SEARCH_MODE", "linear")).lower()
        if mode not in self.VALID_SEARCH_MODES:
            raise ValueError("search_mode must be 'linear' or 'tree'")
        if branch_factor <= 0:
            raise ValueError("branch_factor must be positive")
        if max_depth < 0:
            raise ValueError("max_depth cannot be negative")
        self.max_retries = max_retries
        self._replanner = replanner or self._default_replanner
        self.search_mode = mode
        self._branch_generator = branch_generator or self._default_branch_generator
        self._scorer = scorer or self._default_scorer
        self._budget_manager = budget_manager
        self._budget_estimator = budget_estimator or self._default_budget_estimator
        self.branch_factor = branch_factor
        self.max_depth = max_depth
        self.max_nodes = max_nodes or max_retries
        self.prune_threshold = prune_threshold

    def executar(self, plano: Any, executor: Executor) -> LoopResult:
        """Execute a plan using the configured search mode."""

        if self.search_mode == "tree":
            return self._executar_tree(plano, executor)
        return self._executar_linear(plano, executor)

    def _executar_linear(self, plano: Any, executor: Executor) -> LoopResult:
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

    def _executar_tree(self, plano: Any, executor: Executor) -> LoopResult:
        root = _SearchNode("node-0", plano, 0, 1.0, 0, "branch-0")
        frontier = [root]
        history: List[Dict[str, Any]] = []
        best_node = root
        last_result: Dict[str, Any] = {}
        executed = 0
        order = 1

        while frontier and executed < self.max_nodes:
            frontier.sort(key=lambda node: (-node.score, node.order))
            node = frontier.pop(0)
            projected_cost = float(self._budget_estimator(node.plan))
            if self._would_exceed_branch_budget(node, projected_cost):
                history.append(self._history_entry(node, {"success": False}, pruned=True, prune_reason="budget"))
                continue
            try:
                self._enforce_budget(node, projected_cost)
            except BudgetExceededError as exc:
                history.append(
                    self._history_entry(
                        node,
                        {"success": False, "error": str(exc)},
                        pruned=True,
                        prune_reason="budget",
                    )
                )
                continue

            last_result = executor(node.plan)
            executed += 1
            node_cost = projected_cost + float(last_result.get("cost", 0.0) or 0.0)
            history.append(self._history_entry(node, last_result, branch_cost=node.branch_cost + node_cost))
            if last_result.get("success") is True:
                return LoopResult(
                    status=LoopStatus.SUCCESS,
                    attempts=executed,
                    final_plan=node.plan,
                    result=last_result,
                    history=history,
                )
            if self._is_hitl_terminal(last_result):
                history[-1]["hitl_terminal"] = True
                continue
            if node.depth >= self.max_depth:
                continue

            children = self._branch_generator(node.plan, last_result, node.depth + 1)[: self.branch_factor]
            for child in children:
                score = max(0.0, min(1.0, float(self._scorer(child, last_result))))
                child_node = _SearchNode(
                    node_id=f"node-{order}",
                    plan=child,
                    depth=node.depth + 1,
                    score=score,
                    order=order,
                    branch_id=node.branch_id if node.depth else f"branch-{order}",
                    branch_cost=node.branch_cost + node_cost,
                )
                order += 1
                if score < self.prune_threshold:
                    history.append(
                        self._history_entry(
                            child_node,
                            {"success": False},
                            pruned=True,
                            prune_reason="score",
                        )
                    )
                    continue
                frontier.append(child_node)
                if score >= best_node.score:
                    best_node = child_node

        return LoopResult(
            status=LoopStatus.FAILED,
            attempts=executed,
            final_plan=best_node.plan,
            result=last_result,
            history=history,
        )

    def _default_replanner(self, plano: Any, resultado: Dict[str, Any]) -> Any:
        if isinstance(plano, dict):
            updated = dict(plano)
            updated.setdefault("replanning_notes", []).append(resultado.get("error", "failed"))
            return updated
        return plano

    def _default_branch_generator(self, plano: Any, resultado: Dict[str, Any], _: int) -> List[Any]:
        return [self._replanner(plano, resultado)]

    @staticmethod
    def _default_scorer(_: Any, resultado: Dict[str, Any]) -> float:
        if resultado.get("success") is True:
            return 1.0
        return float(resultado.get("score", 0.0) or 0.0)

    @staticmethod
    def _default_budget_estimator(plano: Any) -> float:
        if isinstance(plano, dict):
            return float(plano.get("estimated_cost", 0.0) or 0.0)
        return 0.0

    def _enforce_budget(self, node: _SearchNode, projected_cost: float) -> None:
        if self._budget_manager is None:
            return
        self._budget_manager.enforce_call(
            provider="tree_search",
            projected_cost=projected_cost,
            trace_id=f"tree:{node.branch_id}:{node.node_id}",
        )

    def _would_exceed_branch_budget(self, node: _SearchNode, projected_cost: float) -> bool:
        if self._budget_manager is None:
            return False
        branch_limit = self._budget_manager.branch_limit_usd
        return branch_limit is not None and node.branch_cost + projected_cost > branch_limit

    @staticmethod
    def _is_hitl_terminal(result: Dict[str, Any]) -> bool:
        status = str(result.get("status", "")).lower()
        return bool(result.get("hitl_required")) or status in {"pending", "denied", "error", "hitl_pending"}

    @staticmethod
    def _history_entry(
        node: _SearchNode,
        result: Dict[str, Any],
        *,
        pruned: bool = False,
        prune_reason: str | None = None,
        branch_cost: float | None = None,
    ) -> Dict[str, Any]:
        entry = {
            "node_id": node.node_id,
            "branch_id": node.branch_id,
            "depth": node.depth,
            "score": node.score,
            "plan": node.plan,
            "result": result,
        }
        if branch_cost is not None:
            entry["branch_cost"] = branch_cost
        if pruned:
            entry["pruned"] = True
            entry["prune_reason"] = prune_reason
        return entry
