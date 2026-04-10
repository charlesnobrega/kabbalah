"""End-to-end orchestration tests for complete workflow.

**Validates: Requirements 1, 5, 6, 7**
"""

import pytest
from hypothesis import given, strategies as st
from kabbalah.intake_node import IntakeNode
from kabbalah.root_orchestrator import RootOrchestrator
from kabbalah.domain_orchestrator import DomainOrchestrator
from kabbalah.synthesizer import Synthesizer
from kabbalah.models import UserRequest


class TestEndToEndOrchestration:
    """End-to-end orchestration tests."""
    
    def test_complete_orchestration_workflow(self):
        """Test complete orchestration from request to delivery package."""
        # Step 1: Parse request
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
        
        # Verify specification
        assert spec.run_id == run_id
        assert spec.project_name == "E-Commerce Platform"
        assert len(spec.domains) > 0
        
        # Step 2: Decompose into branches
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Verify branches
        assert len(branches) == len(spec.domains)
        for branch in branches:
            assert branch.run_id == run_id
            assert branch.branch_id
            assert branch.domain_name in spec.domains
        
        # Step 3: Execute branches
        results = root_orch.execute_branches(branches)
        
        # Verify results
        assert len(results) == len(branches)
        for branch_id, result in results.items():
            assert result.run_id == run_id
            assert result.status in ["success", "error", "timeout"]
        
        # Step 4: Synthesize results
        synthesizer = Synthesizer()
        package = synthesizer.generate_delivery_package(
            run_id,
            spec.project_name,
            results,
            spec
        )
        
        # Verify delivery package
        assert package.run_id == run_id
        assert package.project_name == spec.project_name
        assert isinstance(package.execution_report, dict)
        assert isinstance(package.trace_information, dict)
    
    def test_orchestration_with_multiple_domains(self):
        """Test orchestration with multiple domains."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Complex System",
            project_description="Build backend, frontend, infrastructure, testing, and documentation"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should have multiple domains
        assert len(spec.domains) >= 2
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Should have branch for each domain
        assert len(branches) == len(spec.domains)
        
        # All branches should have unique IDs
        branch_ids = [b.branch_id for b in branches]
        assert len(branch_ids) == len(set(branch_ids))
    
    def test_orchestration_with_dependencies(self):
        """Test orchestration respects dependencies."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Dependent System",
            project_description="Build backend and frontend"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Frontend should depend on backend
        assert "backend" in spec.dependencies.get("frontend", [])
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        # All branches should complete successfully
        for result in results.values():
            assert result.status == "success"
    
    def test_trace_id_propagation_through_all_levels(self):
        """Test that trace_id is propagated through all levels."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Trace Test",
            project_description="Test trace propagation"
        )
        
        spec, run_id = intake.parse_request(request)
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Verify run_id in branches
        for branch in branches:
            assert branch.run_id == run_id
        
        # Spawn leaf nodes and verify trace_id
        domain_orch = DomainOrchestrator()
        for branch in branches:
            leaf_nodes = domain_orch.spawn_leaf_nodes(branch, run_id, branch.branch_id)
            
            # Verify trace_id format
            for leaf_node in leaf_nodes:
                trace_parts = leaf_node.trace_id.split(":")
                assert len(trace_parts) == 3
                assert trace_parts[0] == run_id
                assert trace_parts[1] == branch.branch_id
                assert trace_parts[2] == leaf_node.leaf_id
    
    def test_orchestration_with_all_components(self):
        """Test orchestration using all components together."""
        # Create request
        intake = IntakeNode()
        request = UserRequest(
            project_name="Full System",
            project_description="Build a complete system with backend, frontend, infrastructure, testing, and documentation"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Decompose
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Execute branches
        results = root_orch.execute_branches(branches)
        
        # Spawn and execute leaf nodes for each branch
        domain_orch = DomainOrchestrator()
        all_leaf_results = []
        
        for branch in branches:
            leaf_nodes = domain_orch.spawn_leaf_nodes(branch, run_id, branch.branch_id)
            leaf_results = domain_orch.execute_leaf_nodes(leaf_nodes)
            all_leaf_results.extend(leaf_results)
        
        # Synthesize
        synthesizer = Synthesizer()
        package = synthesizer.generate_delivery_package(
            run_id,
            spec.project_name,
            results,
            spec
        )
        
        # Verify complete workflow
        assert len(branches) > 0
        assert len(results) == len(branches)
        assert len(all_leaf_results) > 0
        assert package.run_id == run_id
        assert package.project_name == spec.project_name


class TestEndToEndProperties:
    """Property-based tests for end-to-end orchestration.
    
    **Validates: Requirements 1, 5, 6, 7**
    """
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_complete_workflow_produces_valid_package(self, project_name, project_description):
        """Property: Complete workflow always produces valid delivery package.
        
        **Validates: Requirements 1, 6, 7**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, run_id = intake.parse_request(request)
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        synthesizer = Synthesizer()
        package = synthesizer.generate_delivery_package(
            run_id,
            project_name,
            results,
            spec
        )
        
        # Verify package is valid
        assert package.run_id == run_id
        assert package.project_name == project_name
        assert isinstance(package.artifacts, dict)
        assert isinstance(package.execution_report, dict)
        assert isinstance(package.trace_information, dict)
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_trace_id_consistency_throughout_workflow(self, project_name, project_description):
        """Property: Trace IDs are consistent throughout workflow.
        
        **Validates: Requirements 1, 5**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, run_id = intake.parse_request(request)
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Verify run_id in all branches
        for branch in branches:
            assert branch.run_id == run_id
        
        # Verify branch_ids are unique
        branch_ids = [b.branch_id for b in branches]
        assert len(branch_ids) == len(set(branch_ids))
        
        # Verify leaf_ids are unique per branch
        domain_orch = DomainOrchestrator()
        for branch in branches:
            leaf_nodes = domain_orch.spawn_leaf_nodes(branch, run_id, branch.branch_id)
            
            leaf_ids = [n.leaf_id for n in leaf_nodes]
            assert len(leaf_ids) == len(set(leaf_ids))
            
            # Verify trace_id format
            for leaf_node in leaf_nodes:
                parts = leaf_node.trace_id.split(":")
                assert len(parts) == 3
                assert parts[0] == run_id
                assert parts[1] == branch.branch_id
                assert parts[2] == leaf_node.leaf_id
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_all_branches_execute_successfully(self, project_name, project_description):
        """Property: All branches execute successfully in workflow.
        
        **Validates: Requirements 1, 6**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, run_id = intake.parse_request(request)
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        # All branches should have results
        assert len(results) == len(branches)
        
        # All results should be successful
        for result in results.values():
            assert result.status == "success"
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_dependencies_are_respected(self, project_name, project_description):
        """Property: Dependencies are respected during execution.
        
        **Validates: Requirements 1, 7**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Verify dependencies are valid
        for domain, deps in spec.dependencies.items():
            for dep in deps:
                assert dep in spec.domains
        
        root_orch = RootOrchestrator()
        branches = root_orch.decompose_specification(spec, run_id)
        
        # Verify branch dependencies match specification
        for branch in branches:
            expected_deps = spec.dependencies.get(branch.domain_name, [])
            assert set(branch.dependencies) == set(expected_deps)
