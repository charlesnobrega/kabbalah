"""Unit tests for RootOrchestrator class."""

import pytest
from hypothesis import given, strategies as st
from kabbalah.root_orchestrator import (
    RootOrchestrator, DomainBranch, BranchResult,
    DecompositionError, ExecutionError
)
from kabbalah.models import Specification, UserRequest
from kabbalah.intake_node import IntakeNode


class TestRootOrchestratorDecomposition:
    """Tests for specification decomposition."""
    
    def test_decompose_specification_with_null_specification(self):
        """Test that null specification raises DecompositionError."""
        orchestrator = RootOrchestrator()
        with pytest.raises(DecompositionError, match="Specification cannot be null"):
            orchestrator.decompose_specification(None, "run_2026_04_06_001")
    
    def test_decompose_specification_with_null_run_id(self):
        """Test that null run_id raises DecompositionError."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, _ = intake.parse_request(request)
        
        with pytest.raises(DecompositionError, match="run_id cannot be null"):
            orchestrator.decompose_specification(spec, None)
    
    def test_decompose_specification_with_empty_run_id(self):
        """Test that empty run_id raises DecompositionError."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, _ = intake.parse_request(request)
        
        with pytest.raises(DecompositionError, match="run_id cannot be null"):
            orchestrator.decompose_specification(spec, "")
    
    def test_decompose_specification_returns_branches(self):
        """Test that decomposition returns list of branches."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        assert isinstance(branches, list)
        assert len(branches) > 0
    
    def test_decompose_specification_creates_branch_for_each_domain(self):
        """Test that each domain gets a branch."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        # Should have one branch per domain
        assert len(branches) == len(spec.domains)
        
        # Each domain should have a corresponding branch
        branch_domains = {b.domain_name for b in branches}
        assert branch_domains == set(spec.domains)
    
    def test_decompose_specification_generates_unique_branch_ids(self):
        """Test that all branch_ids are unique."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        branch_ids = [b.branch_id for b in branches]
        assert len(branch_ids) == len(set(branch_ids))
    
    def test_decompose_specification_branch_id_format(self):
        """Test that branch_ids have correct format."""
        import re
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        for branch in branches:
            # Format: branch_{domain}_{NNN}
            assert re.match(r"^branch_\w+_\d{3}$", branch.branch_id)
    
    def test_decompose_specification_preserves_run_id(self):
        """Test that run_id is preserved in branches."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        for branch in branches:
            assert branch.run_id == run_id
    
    def test_decompose_specification_sets_dependencies(self):
        """Test that dependencies are set correctly."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        # Find frontend branch
        frontend_branch = next((b for b in branches if b.domain_name == "frontend"), None)
        if frontend_branch:
            # Frontend should depend on backend
            assert "backend" in frontend_branch.dependencies
    
    def test_decompose_specification_sets_provider(self):
        """Test that provider is set for each branch."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        for branch in branches:
            assert branch.provider
            assert isinstance(branch.provider, str)
    
    def test_decompose_specification_sets_model(self):
        """Test that model is set for each branch."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        for branch in branches:
            assert branch.model
            assert isinstance(branch.model, str)
    
    def test_decompose_specification_creates_tasks(self):
        """Test that tasks are created for each branch."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        for branch in branches:
            assert isinstance(branch.tasks, list)
            assert len(branch.tasks) > 0


class TestRootOrchestratorExecution:
    """Tests for branch execution."""
    
    def test_execute_branches_with_empty_list(self):
        """Test that empty branches list raises ExecutionError."""
        orchestrator = RootOrchestrator()
        with pytest.raises(ExecutionError, match="Branches list cannot be empty"):
            orchestrator.execute_branches([])
    
    def test_execute_branches_returns_results(self):
        """Test that execution returns results."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        assert isinstance(results, dict)
        assert len(results) == len(branches)
    
    def test_execute_branches_results_have_branch_ids(self):
        """Test that results are keyed by branch_id."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        branch_ids = {b.branch_id for b in branches}
        result_ids = set(results.keys())
        
        assert branch_ids == result_ids
    
    def test_execute_branches_results_have_status(self):
        """Test that results have status field."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        for result in results.values():
            assert result.status in ["success", "error", "timeout"]
    
    def test_execute_branches_respects_dependencies(self):
        """Test that dependencies are respected during execution."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        # All branches should complete successfully
        for result in results.values():
            assert result.status == "success"
    
    def test_execute_branches_preserves_run_id(self):
        """Test that run_id is preserved in results."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        for result in results.values():
            assert result.run_id == run_id
    
    def test_execute_branches_sets_timing(self):
        """Test that execution timing is recorded."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        for result in results.values():
            assert result.start_time > 0
            assert result.end_time > 0
            assert result.duration >= 0
            assert result.end_time >= result.start_time


class TestRootOrchestratorBranchIdGeneration:
    """Tests for branch_id generation."""
    
    def test_branch_id_uniqueness_across_calls(self):
        """Test that branch_ids are unique across multiple calls."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches1 = orchestrator.decompose_specification(spec, run_id)
        branches2 = orchestrator.decompose_specification(spec, run_id)
        
        ids1 = {b.branch_id for b in branches1}
        ids2 = {b.branch_id for b in branches2}
        
        # IDs should be different (counter incremented)
        assert ids1 != ids2
    
    def test_branch_id_counter_increments(self):
        """Test that branch_id counter increments correctly."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        branches1 = orchestrator.decompose_specification(spec, run_id)
        branches2 = orchestrator.decompose_specification(spec, run_id)
        
        # Extract counters
        backend1 = next((b for b in branches1 if b.domain_name == "backend"), None)
        backend2 = next((b for b in branches2 if b.domain_name == "backend"), None)
        
        if backend1 and backend2:
            counter1 = int(backend1.branch_id.split("_")[-1])
            counter2 = int(backend2.branch_id.split("_")[-1])
            assert counter2 == counter1 + 1


class TestRootOrchestratorIntegration:
    """Integration tests for RootOrchestrator."""
    
    def test_full_decomposition_and_execution_workflow(self):
        """Test complete workflow from specification to execution."""
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name="E-Commerce Platform",
            project_description="Build a scalable e-commerce platform with payment processing, inventory management, and user authentication. Deploy to AWS with Docker.",
            scope="Full-stack web application",
            constraints=["Must support 10k concurrent users", "Must have 99.9% uptime"],
            resources={"budget": 50000, "team_size": 5},
            metadata={"client": "Acme Corp", "deadline": "2026-06-30"}
        )
        
        spec, run_id = intake.parse_request(request)
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        # Verify workflow
        assert len(branches) > 0
        assert len(results) == len(branches)
        
        for result in results.values():
            assert result.status == "success"
            assert result.run_id == run_id


class TestRootOrchestratorProperties:
    """Property-based tests for RootOrchestrator.
    
    **Validates: Requirements 1, 2**
    """
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_decomposition_creates_valid_branches(self, project_name, project_description):
        """Property: Decomposition always creates valid branches.
        
        **Validates: Requirements 1, 2**
        """
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        # Verify all branches are valid
        assert len(branches) > 0
        for branch in branches:
            assert branch.run_id == run_id
            assert branch.branch_id
            assert branch.domain_name
            assert branch.provider
            assert branch.model
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_branch_ids_are_unique(self, project_name, project_description):
        """Property: All branch_ids are unique within a decomposition.
        
        **Validates: Requirements 1, 2**
        """
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        
        branch_ids = [b.branch_id for b in branches]
        assert len(branch_ids) == len(set(branch_ids))
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_execution_completes_all_branches(self, project_name, project_description):
        """Property: Execution completes all branches successfully.
        
        **Validates: Requirements 1, 6**
        """
        orchestrator = RootOrchestrator()
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        
        branches = orchestrator.decompose_specification(spec, run_id)
        results = orchestrator.execute_branches(branches)
        
        # All branches should have results
        assert len(results) == len(branches)
        
        # All results should have status
        for result in results.values():
            assert result.status in ["success", "error", "timeout"]


# Import hypothesis strategies
from hypothesis import strategies as st
