from hypothesis import given
from hypothesis import strategies as st

from kabbalah.autonomy_loop import AutonomyLoop, LoopStatus
from kabbalah.budget_manager import BudgetLedger, BudgetManager


def test_tree_search_executes_highest_scored_branch_first():
    executed = []

    def executor(plan):
        executed.append(plan["name"])
        return {"success": plan["name"] == "high", "score": plan.get("score", 0.0)}

    def generator(plan, result, depth):
        assert depth == 1
        return [{"name": "low", "score": 0.2}, {"name": "high", "score": 0.9}]

    loop = AutonomyLoop(
        search_mode="tree",
        branch_generator=generator,
        scorer=lambda plan, result: plan["score"],
        branch_factor=2,
        max_nodes=3,
    )

    result = loop.executar({"name": "root"}, executor)

    assert result.status == LoopStatus.SUCCESS
    assert result.final_plan["name"] == "high"
    assert executed == ["root", "high"]


def test_tree_search_prunes_below_score_threshold():
    def executor(plan):
        return {"success": False, "score": plan.get("score", 0.0)}

    loop = AutonomyLoop(
        search_mode="tree",
        branch_generator=lambda plan, result, depth: [{"name": "weak", "score": 0.1}],
        scorer=lambda plan, result: plan["score"],
        prune_threshold=0.5,
        max_nodes=2,
    )

    result = loop.executar({"name": "root"}, executor)

    assert result.status == LoopStatus.FAILED
    assert any(entry.get("pruned") and entry.get("prune_reason") == "score" for entry in result.history)


def test_tree_search_does_not_execute_branch_over_budget(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    manager = BudgetManager(ledger, branch_limit_usd=0.05, mode="block")
    executed = []

    def executor(plan):
        executed.append(plan["name"])
        return {"success": False}

    loop = AutonomyLoop(
        search_mode="tree",
        branch_generator=lambda plan, result, depth: [{"name": "expensive", "estimated_cost": 0.06}],
        budget_manager=manager,
        budget_estimator=lambda plan: float(plan.get("estimated_cost", 0.0)),
        max_nodes=2,
    )

    result = loop.executar({"name": "root", "estimated_cost": 0.0}, executor)

    assert executed == ["root"]
    assert any(entry.get("pruned") and entry.get("prune_reason") == "budget" for entry in result.history)


def test_tree_search_treats_hitl_pending_as_terminal_branch():
    generated = []

    def executor(plan):
        if plan["name"] == "needs-human":
            return {"success": False, "status": "pending", "hitl_required": True}
        return {"success": False}

    def generator(plan, result, depth):
        generated.append(plan["name"])
        if plan["name"] == "root":
            return [{"name": "needs-human", "score": 1.0}]
        return [{"name": "must-not-run", "score": 1.0}]

    loop = AutonomyLoop(
        search_mode="tree",
        branch_generator=generator,
        scorer=lambda plan, result: plan.get("score", 0.0),
        max_nodes=3,
    )

    result = loop.executar({"name": "root"}, executor)

    assert result.status == LoopStatus.FAILED
    assert generated == ["root"]
    assert any(entry.get("hitl_terminal") for entry in result.history)


@given(st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=5))
def test_tree_pruning_is_deterministic_for_same_scores(scores):
    def run_once():
        loop = AutonomyLoop(
            search_mode="tree",
            branch_generator=lambda plan, result, depth: [
                {"name": f"node-{index}", "score": score} for index, score in enumerate(scores)
            ],
            scorer=lambda plan, result: plan["score"],
            prune_threshold=0.5,
            max_nodes=1,
        )
        return loop.executar({"name": "root"}, lambda plan: {"success": False})

    first = run_once()
    second = run_once()

    assert [
        (entry["node_id"], entry["plan"], entry.get("pruned"), entry.get("prune_reason"))
        for entry in first.history
    ] == [
        (entry["node_id"], entry["plan"], entry.get("pruned"), entry.get("prune_reason"))
        for entry in second.history
    ]

