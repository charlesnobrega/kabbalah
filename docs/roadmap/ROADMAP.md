# Roadmap

This roadmap is forward-looking. It does not imply the listed systems are implemented today.

## 1. Budget Manager

- Objective: track provider/tool cost, token usage, and per-run limits.
- Dependencies: provider responses with reliable token/cost metadata, trace ids.
- Risks: inaccurate provider accounting and missing failed-call costs.
- Estimated complexity: medium.
- Rollback considerations: keep budget enforcement warn-only before blocking execution.

## 2. Policy Engine

- Objective: centralize FSM, role, contract, memory, tool, and Day 2 decisions.
- Dependencies: existing enforcement modules, audit log format.
- Risks: bypass paths if integration is partial.
- Estimated complexity: high.
- Rollback considerations: keep existing modules callable independently.

## 3. Skill Registry

- Objective: register external skills with metadata, permissions, sandbox profile, and approval state.
- Dependencies: policy engine, tool restrictions, audit requirements.
- Risks: supply-chain exposure and unsafe tool expansion.
- Estimated complexity: high.
- Rollback considerations: registry entries default disabled and removable without code changes.

## 4. Memory Evolution

- Objective: separate working, episodic, long-term, and knowledge memory.
- Dependencies: memory governance, backend reliability, trace metadata.
- Risks: stale context, leakage across roles, inconsistent retrieval.
- Estimated complexity: high.
- Rollback considerations: preserve JSONL baseline and migration scripts.

## 5. Meta Orchestrator

- Objective: coordinate multiple orchestrator strategies and choose execution plans.
- Dependencies: stable tree runtime, budget manager, policy engine.
- Risks: planner overreach and difficult debugging.
- Estimated complexity: high.
- Rollback considerations: keep single tree orchestrator as fallback.

## 6. Agent Reputation

- Objective: score agents/providers/skills by reliability, cost, latency, and review outcomes.
- Dependencies: observability, evaluator metrics, audit history.
- Risks: biased scores and stale performance signals.
- Estimated complexity: medium.
- Rollback considerations: reputation affects recommendations before enforcement.

## 7. Meta Evaluator

- Objective: evaluate outputs across correctness, safety, completeness, and policy compliance.
- Dependencies: artifacts, traces, policy decisions, test hooks.
- Risks: false confidence and evaluator drift.
- Estimated complexity: high.
- Rollback considerations: keep evaluator advisory until validated.

## 8. Graph Runtime

- Objective: evolve from strict tree execution to DAG/graph workflows.
- Dependencies: policy engine, trace propagation, state recovery, scheduler.
- Risks: cycles, partial failure recovery, complex rollback.
- Estimated complexity: very high.
- Rollback considerations: maintain tree runtime compatibility and graph-to-tree fallback for simple workflows.
