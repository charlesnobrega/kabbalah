"""Tests for append-only LLM consumption ledger."""

from kabbalah.budget_manager import BudgetLedger
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
