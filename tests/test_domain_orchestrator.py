"""Unit tests for DomainOrchestrator class."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kabbalah.domain_orchestrator import DomainExecutionError, DomainOrchestrator, LeafNode, SpawnError
from kabbalah.intake_node import IntakeNode
from kabbalah.llm_gateway import ModelProfile, ProviderSelection
from kabbalah.models import UserRequest
from kabbalah.providers.base import ProviderResponse
from kabbalah.root_orchestrator import RootOrchestrator


class TestDomainOrchestratorSpawning:
    """Tests for leaf node spawning."""

    def test_spawn_leaf_nodes_with_null_branch(self):
        """Test that null branch raises SpawnError."""
        orchestrator = DomainOrchestrator()
        with pytest.raises(SpawnError, match="Branch cannot be null"):
            orchestrator.spawn_leaf_nodes(None, "run_2026_04_06_001", "branch_backend_001")

    def test_spawn_leaf_nodes_with_null_run_id(self):
        """Test that null run_id raises SpawnError."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        with pytest.raises(SpawnError, match="run_id cannot be null"):
            orchestrator.spawn_leaf_nodes(branches[0], None, "branch_backend_001")

    def test_spawn_leaf_nodes_with_null_branch_id(self):
        """Test that null branch_id raises SpawnError."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        with pytest.raises(SpawnError, match="branch_id cannot be null"):
            orchestrator.spawn_leaf_nodes(branches[0], run_id, None)

    def test_spawn_leaf_nodes_returns_leaf_nodes(self):
        """Test that spawning returns list of leaf nodes."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        assert isinstance(leaf_nodes, list)
        assert len(leaf_nodes) > 0

    def test_spawn_leaf_nodes_generates_unique_leaf_ids(self):
        """Test that all leaf_ids are unique."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        leaf_ids = [n.leaf_id for n in leaf_nodes]
        assert len(leaf_ids) == len(set(leaf_ids))

    def test_spawn_leaf_nodes_leaf_id_format(self):
        """Test that leaf_ids have correct format."""
        import re

        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        for leaf_node in leaf_nodes:
            # Format: leaf_{domain}_{NNN}
            assert re.match(r"^leaf_\w+_\d{3}$", leaf_node.leaf_id)

    def test_spawn_leaf_nodes_generates_trace_ids(self):
        """Test that trace_ids are generated correctly."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        for leaf_node in leaf_nodes:
            # Format: run_id:branch_id:leaf_id
            assert leaf_node.trace_id == f"{run_id}:{branches[0].branch_id}:{leaf_node.leaf_id}"

    def test_spawn_leaf_nodes_preserves_provider(self):
        """Test that provider is preserved from branch."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        for leaf_node in leaf_nodes:
            assert leaf_node.provider == branches[0].provider

    def test_spawn_leaf_nodes_preserves_model(self):
        """Test that model is preserved from branch."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        for leaf_node in leaf_nodes:
            assert leaf_node.model == branches[0].model


class TestDomainOrchestratorExecution:
    """Tests for leaf node execution."""

    def _leaf_node(self):
        return LeafNode(
            run_id="run_001",
            branch_id="branch_backend_001",
            leaf_id="leaf_backend_001",
            trace_id="run_001:branch_backend_001:leaf_backend_001",
            task_id="task_001",
            task_type="implementation",
            description="Implement an API endpoint",
            provider="gateway",
            model="auto",
            metadata={"domain": "backend", "task_inputs": {"path": "/health"}},
        )

    def test_execute_leaf_node_without_gateway_returns_skipped(self):
        """Leaf execution without gateway must not claim fake success."""
        orchestrator = DomainOrchestrator()

        result = orchestrator._execute_leaf_node(self._leaf_node())

        assert result.status == "skipped"
        assert result.artifacts == []
        assert result.metadata["reason"] == "llm_gateway_not_configured"

    def test_execute_leaf_node_with_gateway_returns_provider_artifact(self):
        """Leaf execution with gateway uses provider response as real artifact."""

        class Provider:
            def execute_request(self, request, timeout=30.0):
                assert request["messages"][0]["role"] == "system"
                assert "Implement an API endpoint" in request["messages"][1]["content"]
                return ProviderResponse(
                    content="real artifact",
                    model="mock-model",
                    tokens_used=42,
                    cost=0.001,
                    latency_ms=12.5,
                )

        class Gateway:
            def select_provider(self, *, role, capability, budget_hint=None):
                assert role == "Leaf_Builder"
                assert capability == "code"
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

        result = DomainOrchestrator(llm_gateway=Gateway())._execute_leaf_node(self._leaf_node())

        assert result.status == "success"
        assert result.artifacts == [
            {
                "type": "llm_response",
                "content": "real artifact",
                "model": "mock-model",
            }
        ]
        assert result.metadata["provider"] == "mock"
        assert result.metadata["profile"] == "mock-profile"
        assert result.metadata["tokens_used"] == 42
        assert result.metadata["cost"] == 0.001
        assert result.metadata["latency_ms"] == 12.5

    def test_execute_leaf_node_provider_error_returns_failure(self):
        """Provider errors are captured as leaf failures, not tree crashes."""

        class Provider:
            def execute_request(self, request, timeout=30.0):
                raise RuntimeError("provider unavailable")

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

        result = DomainOrchestrator(llm_gateway=Gateway())._execute_leaf_node(self._leaf_node())

        assert result.status == "failure"
        assert "provider unavailable" in result.metadata["error"]

    def test_execute_leaf_node_falls_back_to_next_gateway_candidate(self):
        """Provider connection failure should try the next candidate before failing."""

        class FailingProvider:
            def execute_request(self, request, timeout=30.0):
                raise ConnectionError("ollama refused connection")

        class WorkingProvider:
            def execute_request(self, request, timeout=30.0):
                return ProviderResponse(
                    content="fallback artifact",
                    model="groq-model",
                    tokens_used=12,
                    cost=0.0001,
                    latency_ms=8.0,
                )

        class Gateway:
            def __init__(self):
                self.marked_unavailable = []

            def select_providers(self, *, role, capability, budget_hint=None, trace_id="gateway:selection"):
                assert trace_id == "run_001:branch_backend_001:leaf_backend_001"
                return [
                    ProviderSelection(
                        profile=ModelProfile(
                            name="local-ollama",
                            provider_name="ollama_local",
                            model="llama3.1",
                            roles={"Leaf_Builder"},
                            capabilities={"code"},
                            context_window=8192,
                            input_cost_per_1m_tokens=0.0,
                            output_cost_per_1m_tokens=0.0,
                            license_type="open",
                            location="local",
                            tier="local",
                        ),
                        provider=FailingProvider(),
                    ),
                    ProviderSelection(
                        profile=ModelProfile(
                            name="groq-fast",
                            provider_name="groq_compatible",
                            model="groq-model",
                            roles={"Leaf_Builder"},
                            capabilities={"code"},
                            context_window=8192,
                            input_cost_per_1m_tokens=0.05,
                            output_cost_per_1m_tokens=0.08,
                            license_type="agregador",
                            location="cloud",
                            tier="fast",
                        ),
                        provider=WorkingProvider(),
                    ),
                ]

            def mark_unavailable(self, profile, error):
                self.marked_unavailable.append((profile.name, error))

        gateway = Gateway()
        result = DomainOrchestrator(llm_gateway=gateway)._execute_leaf_node(self._leaf_node())

        assert result.status == "success"
        assert result.metadata["provider"] == "groq_compatible"
        assert result.metadata["failed_profiles"] == [
            {"profile": "local-ollama", "provider": "ollama_local", "error": "ollama refused connection"}
        ]
        assert gateway.marked_unavailable == [("local-ollama", "ollama refused connection")]
        assert result.artifacts[0]["content"] == "fallback artifact"

    def test_execute_leaf_node_calculates_cost_from_profile_usage_when_provider_cost_is_zero(self, tmp_path):
        """Ledger cost must use ModelProfile pricing when a compatible provider reports zero cost."""
        from kabbalah.budget_manager import BudgetLedger

        ledger = BudgetLedger(tmp_path / "state.sqlite3")

        class Provider:
            def execute_request(self, request, timeout=30.0):
                return ProviderResponse(
                    content="priced artifact",
                    model="priced-model",
                    tokens_used=3000,
                    cost=0.0,
                    latency_ms=9.0,
                    raw_response={
                        "usage": {
                            "prompt_tokens": 1000,
                            "completion_tokens": 2000,
                            "total_tokens": 3000,
                        }
                    },
                )

        class Gateway:
            def select_provider(self, *, role, capability, budget_hint=None, trace_id="gateway:selection"):
                return ProviderSelection(
                    profile=ModelProfile(
                        name="priced-profile",
                        provider_name="groq_compatible",
                        model="priced-model",
                        roles={"Leaf_Builder"},
                        capabilities={"code"},
                        context_window=8192,
                        input_cost_per_1m_tokens=0.05,
                        output_cost_per_1m_tokens=0.08,
                        license_type="agregador",
                        location="cloud",
                        tier="fast",
                    ),
                    provider=Provider(),
                )

        result = DomainOrchestrator(llm_gateway=Gateway(), budget_ledger=ledger)._execute_leaf_node(self._leaf_node())

        assert result.status == "success"
        assert result.metadata["cost"] == pytest.approx(0.00021)
        assert ledger.list_entries()[0]["cost"] == pytest.approx(0.00021)

    def test_execute_leaf_nodes_with_empty_list(self):
        """Test that empty leaf nodes list raises DomainExecutionError."""
        orchestrator = DomainOrchestrator()
        with pytest.raises(DomainExecutionError, match="Leaf nodes list cannot be empty"):
            orchestrator.execute_leaf_nodes([])

    def test_execute_leaf_nodes_returns_results(self):
        """Test that execution returns results."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        results = orchestrator.execute_leaf_nodes(leaf_nodes)

        assert isinstance(results, list)
        assert len(results) == len(leaf_nodes)

    def test_execute_leaf_nodes_results_have_status(self):
        """Test that results have status field."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        results = orchestrator.execute_leaf_nodes(leaf_nodes)

        for result in results:
            assert result.status in ["success", "skipped", "failure", "error", "timeout"]

    def test_execute_leaf_nodes_preserves_trace_id(self):
        """Test that trace_id is preserved in results."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        results = orchestrator.execute_leaf_nodes(leaf_nodes)

        for i, result in enumerate(results):
            assert result.trace_id == leaf_nodes[i].trace_id

    def test_execute_leaf_nodes_sets_timing(self):
        """Test that execution timing is recorded."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        results = orchestrator.execute_leaf_nodes(leaf_nodes)

        for result in results:
            assert result.start_time > 0
            assert result.end_time > 0
            assert result.duration >= 0
            assert result.end_time >= result.start_time


class TestDomainOrchestratorLeafIdGeneration:
    """Tests for leaf_id generation."""

    def test_leaf_id_uniqueness_across_calls(self):
        """Test that leaf_ids are unique across multiple calls."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes1 = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        leaf_nodes2 = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        ids1 = {n.leaf_id for n in leaf_nodes1}
        ids2 = {n.leaf_id for n in leaf_nodes2}

        # IDs should be different (counter incremented)
        assert ids1 != ids2

    def test_leaf_id_counter_increments(self):
        """Test that leaf_id counter increments correctly."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name="Test", project_description="Test")
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes1 = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        leaf_nodes2 = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        # Extract counters
        counter1 = int(leaf_nodes1[0].leaf_id.split("_")[-1])
        counter2 = int(leaf_nodes2[0].leaf_id.split("_")[-1])

        assert counter2 == counter1 + 1


class TestDomainOrchestratorIntegration:
    """Integration tests for DomainOrchestrator."""

    def test_full_spawning_and_execution_workflow(self):
        """Test complete workflow from branch to leaf execution."""
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="E-Commerce Platform",
            project_description=(
                "Build a scalable e-commerce platform with payment processing, "
                "inventory management, and user authentication. Deploy to AWS with Docker."
            ),
            scope="Full-stack web application",
            constraints=["Must support 10k concurrent users", "Must have 99.9% uptime"],
            resources={"budget": 50000, "team_size": 5},
            metadata={"client": "Acme Corp", "deadline": "2026-06-30"},
        )

        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        for branch in branches:
            leaf_nodes = orchestrator.spawn_leaf_nodes(branch, run_id, branch.branch_id)
            results = orchestrator.execute_leaf_nodes(leaf_nodes)

            # Verify workflow
            assert len(leaf_nodes) > 0
            assert len(results) == len(leaf_nodes)

            for result in results:
                assert result.status == "skipped"
                assert result.run_id == run_id
                assert result.branch_id == branch.branch_id


class TestDomainOrchestratorProperties:
    """Property-based tests for DomainOrchestrator.

    **Validates: Requirements 1, 3**
    """

    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
    )
    def test_spawning_creates_valid_leaf_nodes(self, project_name, project_description):
        """Property: Spawning always creates valid leaf nodes.

        **Validates: Requirements 1, 3**
        """
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name=project_name, project_description=project_description)
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        # Verify all leaf nodes are valid
        assert len(leaf_nodes) > 0
        for leaf_node in leaf_nodes:
            assert leaf_node.run_id == run_id
            assert leaf_node.branch_id == branches[0].branch_id
            assert leaf_node.leaf_id
            assert leaf_node.trace_id

    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
    )
    def test_leaf_ids_are_unique(self, project_name, project_description):
        """Property: All leaf_ids are unique within a spawning.

        **Validates: Requirements 1, 3**
        """
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name=project_name, project_description=project_description)
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        leaf_ids = [n.leaf_id for n in leaf_nodes]
        assert len(leaf_ids) == len(set(leaf_ids))

    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
    )
    def test_trace_ids_are_hierarchical(self, project_name, project_description):
        """Property: All trace_ids are hierarchical (run_id:branch_id:leaf_id).

        **Validates: Requirements 1, 5**
        """
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name=project_name, project_description=project_description)
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)

        for leaf_node in leaf_nodes:
            parts = leaf_node.trace_id.split(":")
            assert len(parts) == 3
            assert parts[0] == run_id
            assert parts[1] == branches[0].branch_id
            assert parts[2] == leaf_node.leaf_id

    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ""),
    )
    def test_execution_completes_all_leaf_nodes(self, project_name, project_description):
        """Property: Execution completes all leaf nodes successfully.

        **Validates: Requirements 1, 14**
        """
        orchestrator = DomainOrchestrator()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(project_name=project_name, project_description=project_description)
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)

        leaf_nodes = orchestrator.spawn_leaf_nodes(branches[0], run_id, branches[0].branch_id)
        results = orchestrator.execute_leaf_nodes(leaf_nodes)

        # All leaf nodes should have results
        assert len(results) == len(leaf_nodes)

        # All results should have status
        for result in results:
            assert result.status in ["success", "skipped", "failure", "error", "timeout"]
