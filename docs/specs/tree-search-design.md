# Tree Search Autonomy Loop

O modo padrão continua `linear`. Tree search só roda quando `search_mode="tree"`
ou `KABBALAH_SEARCH_MODE=tree`.

## Algorithm

1. Execute the root plan.
2. If it fails, generate child plans with the injected `branch_generator`.
3. Score each child with the injected `scorer`.
4. Prune children below `prune_threshold`.
5. Execute the remaining frontier in deterministic order: higher score first,
   then insertion order.
6. Stop on first `result["success"] is True`.
7. Stop as failed when `max_nodes` or `max_depth` is exhausted.

## Scoring

The default scorer is intentionally small: successful results score `1.0`;
failed results use `result["score"]` when present, otherwise `0.0`. Production
callers should inject a domain scorer when they have better acceptance metrics.

## Budget

Before executing a node, the loop asks the optional `BudgetManager` to enforce
the projected cost returned by `budget_estimator(plan)`. The same projected
cost is also tracked in-memory per search branch, so a branch cannot continue
past `BudgetManager.branch_limit_usd` even before a provider ledger entry is
written.

## Pruning

Pruned nodes are recorded in history with `pruned=True` and are never executed.
Budget-pruned nodes include `prune_reason="budget"`.

## HITL

HITL `pending`, `denied`, or `error` results are terminal for that branch. They
are recorded as `hitl_terminal=True` and are not treated as success.

## Fallback

`linear` remains the safe default until the tree mode is validated by
Kabbalah-Bench and real orchestration traces.

