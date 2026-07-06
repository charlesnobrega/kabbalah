"""Tests for append-only LLM consumption ledger and budget enforcement."""

import pytest

from kabbalah.budget_manager import BudgetExceededError, BudgetLedger, BudgetManager
from kabbalah.domain_orchestrator import DomainOrchestrator, LeafNode
from kabbalah.llm_gateway import ModelProfile, ProviderSelection
from kabbalah.providers.base import ProviderResponse


def test_budget_ledger_records_append_only_entries(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")

    ledger.record_call(
        provider="openrouter",
        model="openai/gpt-4o-mini",
        input_tokens=12,
        output_tokens=8,
        total_tokens=20,
        cost=0.0001,
        trace_id="run:branch:leaf",
    )

    entries = ledger.list_entries()

    assert len(entries) == 1
    assert entries[0]["provider"] == "openrouter"
    assert entries[0]["model"] == "openai/gpt-4o-mini"
    assert entries[0]["input_tokens"] == 12
    assert entries[0]["output_tokens"] == 8
    assert entries[0]["total_tokens"] == 20
    assert entries[0]["cost"] == 0.0001
    assert entries[0]["trace_id"] == "run:branch:leaf"
    assert "timestamp" in entries[0]
    assert not hasattr(ledger, "update_entry")
    assert not hasattr(ledger, "delete_entry")


def test_leaf_execution_records_budget_ledger_entry(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")

    class Provider:
        def execute_request(self, request, timeout=30.0):
            return ProviderResponse(
                content="artifact",
                model="mock-model",
                tokens_used=10,
                cost=0.0002,
                latency_ms=5.0,
                raw_response={
                    "usage": {
                        "prompt_tokens": 4,
                        "completion_tokens": 6,
                        "total_tokens": 10,
                    }
                },
            )

    class Gateway:
        def select_provider(self, *, role, capability, budget_hint=None):
            return ProviderSelection(
                profile=ModelProfile(
                    name="mock-profile",
                    provider_name="mock",
                    model="mock-model",
                    roles={"Leaf_Builder"},
                    capabilities={"code"},
                    context_window=8192,
                    input_cost_per_1m_tokens=0.0,
                    output_cost_per_1m_tokens=0.0,
                    license_type="open",
                    location="local",
                    tier="local",
                ),
                provider=Provider(),
            )

    leaf = LeafNode(
        run_id="run",
        branch_id="branch",
        leaf_id="leaf",
        trace_id="run:branch:leaf",
        task_id="task",
        task_type="implementation",
        description="Build artifact",
        provider="gateway",
        model="auto",
    )

    result = DomainOrchestrator(llm_gateway=Gateway(), budget_ledger=ledger)._execute_leaf_node(leaf)

    assert result.status == "success"
    entries = ledger.list_entries()
    assert len(entries) == 1
    assert entries[0]["provider"] == "mock"
    assert entries[0]["model"] == "mock-model"
    assert entries[0]["input_tokens"] == 4
    assert entries[0]["output_tokens"] == 6
    assert entries[0]["total_tokens"] == 10
    assert entries[0]["cost"] == 0.0002
    assert entries[0]["trace_id"] == "run:branch:leaf"


def test_budget_manager_allows_call_inside_configured_limits(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    manager = BudgetManager(
        ledger,
        run_limit_usd=1.00,
        daily_limit_usd=2.00,
        provider_limits_usd={"openrouter": 0.50},
        mode="block",
    )

    decision = manager.enforce_call(
        provider="openrouter",
        projected_cost=0.10,
        trace_id="run-1:branch:leaf",
    )

    assert decision.allowed is True
    assert decision.exceeded == []
    assert decision.mode == "block"


def test_budget_manager_blocks_when_run_limit_would_be_exceeded(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="openrouter",
        model="model",
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        cost=0.90,
        trace_id="run-1:branch:leaf-a",
    )
    manager = BudgetManager(ledger, run_limit_usd=1.00, mode="block")

    with pytest.raises(BudgetExceededError, match="run"):
        manager.enforce_call(
            provider="openrouter",
            projected_cost=0.11,
            trace_id="run-1:branch:leaf-b",
        )


def test_budget_manager_blocks_when_branch_limit_would_be_exceeded(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="openrouter",
        model="model",
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        cost=0.04,
        trace_id="run-1:branch-a:leaf-a",
    )
    manager = BudgetManager(ledger, branch_limit_usd=0.05, mode="block")

    with pytest.raises(BudgetExceededError, match="branch"):
        manager.enforce_call(
            provider="openrouter",
            projected_cost=0.02,
            trace_id="run-1:branch-a:leaf-b",
        )


def test_budget_manager_warn_mode_reports_excess_without_raising(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="groq_compatible",
        model="model",
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        cost=0.06,
        trace_id="run-2:branch:leaf-a",
    )
    manager = BudgetManager(
        ledger,
        provider_limits_usd={"groq_compatible": 0.05},
        mode="warn",
    )

    decision = manager.enforce_call(
        provider="groq_compatible",
        projected_cost=0.01,
        trace_id="run-2:branch:leaf-b",
    )

    assert decision.allowed is False
    assert decision.mode == "warn"
    assert decision.exceeded == ["provider:groq_compatible"]


def test_budget_manager_reads_limits_from_environment(monkeypatch, tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    monkeypatch.setenv("KABBALAH_BUDGET_MODE", "block")
    monkeypatch.setenv("KABBALAH_BUDGET_RUN_USD", "3.50")
    monkeypatch.setenv("KABBALAH_BUDGET_BRANCH_USD", "0.75")
    monkeypatch.setenv("KABBALAH_BUDGET_DAILY_USD", "7.00")
    monkeypatch.setenv("KABBALAH_BUDGET_PROVIDER_OPENROUTER_USD", "1.25")

    manager = BudgetManager.from_env(ledger)

    assert manager.mode == "block"
    assert manager.run_limit_usd == 3.50
    assert manager.branch_limit_usd == 0.75
    assert manager.daily_limit_usd == 7.00
    assert manager.provider_limits_usd == {"openrouter": 1.25}


def test_budget_manager_returns_aggregate_stats(tmp_path):
    ledger = BudgetLedger(tmp_path / "state.sqlite3")
    ledger.record_call(
        provider="openrouter",
        model="model-a",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        cost=0.20,
        trace_id="run-a:branch:leaf",
    )
    ledger.record_call(
        provider="groq_compatible",
        model="model-b",
        input_tokens=20,
        output_tokens=5,
        total_tokens=25,
        cost=0.30,
        trace_id="run-b:branch:leaf",
    )

    stats = BudgetManager(ledger, daily_limit_usd=1.0).get_budget_stats()

    assert stats["mode"] == "warn"
    assert stats["total_cost"] == pytest.approx(0.50)
    assert stats["provider_costs"] == {
        "openrouter": pytest.approx(0.20),
        "groq_compatible": pytest.approx(0.30),
    }
    assert stats["run_costs"] == {
        "run-a": pytest.approx(0.20),
        "run-b": pytest.approx(0.30),
    }
    assert stats["limits"]["daily_usd"] == 1.0
