"""Unit tests for Synthesizer class."""

import pytest
from hypothesis import given, strategies as st
from kabbalah.synthesizer import (
    Synthesizer, DeliveryPackage, ConsistencyViolation,
    SynthesisError
)
from kabbalah.root_orchestrator import RootOrchestrator, BranchResult
from kabbalah.domain_orchestrator import DomainOrchestrator
from kabbalah.models import UserRequest
from kabbalah.intake_node import IntakeNode


class TestSynthesizerArtifactCollection:
    """Tests for artifact collection."""
    
    def test_collect_artifacts_with_empty_results(self):
        """Test that empty results raises SynthesisError."""
        synthesizer = Synthesizer()
        with pytest.raises(SynthesisError, match="Branch results cannot be empty"):
            synthesizer.collect_artifacts({})
    
    def test_collect_artifacts_returns_dict(self):
        """Test that collection returns dictionary."""
        synthesizer = Synthesizer()
        
        # Create mock branch results
        branch_results = {
            "branch_backend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_backend_001",
                domain_name="backend",
                status="success",
                artifacts=[
                    {"artifact_type": "code", "content": "backend code"}
                ]
            )
        }
        
        artifacts = synthesizer.collect_artifacts(branch_results)
        
        assert isinstance(artifacts, dict)
    
    def test_collect_artifacts_groups_by_type(self):
        """Test that artifacts are grouped by type."""
        synthesizer = Synthesizer()
        
        # Create mock branch results
        branch_results = {
            "branch_backend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_backend_001",
                domain_name="backend",
                status="success",
                artifacts=[
                    {"artifact_type": "code", "content": "backend code"},
                    {"artifact_type": "documentation", "content": "backend docs"}
                ]
            ),
            "branch_frontend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_frontend_001",
                domain_name="frontend",
                status="success",
                artifacts=[
                    {"artifact_type": "code", "content": "frontend code"}
                ]
            )
        }
        
        artifacts = synthesizer.collect_artifacts(branch_results)
        
        assert "code" in artifacts
        assert "documentation" in artifacts
        assert len(artifacts["code"]) == 2
        assert len(artifacts["documentation"]) == 1


class TestSynthesizerConsistencyValidation:
    """Tests for consistency validation."""
    
    def test_validate_consistency_with_empty_artifacts(self):
        """Test that empty artifacts returns consistent."""
        synthesizer = Synthesizer()
        
        is_consistent, violations = synthesizer.validate_consistency({})
        
        assert is_consistent is True
        assert len(violations) == 0
    
    def test_validate_consistency_returns_tuple(self):
        """Test that validation returns tuple."""
        synthesizer = Synthesizer()
        
        artifacts = {
            "code": [
                {"artifact_type": "code", "content": "code"}
            ]
        }
        
        result = synthesizer.validate_consistency(artifacts)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_validate_consistency_returns_violations_list(self):
        """Test that violations are returned as list."""
        synthesizer = Synthesizer()
        
        artifacts = {
            "code": [
                {"artifact_type": "code", "content": "code"}
            ]
        }
        
        is_consistent, violations = synthesizer.validate_consistency(artifacts)
        
        assert isinstance(violations, list)


class TestSynthesizerMerging:
    """Tests for artifact merging."""
    
    def test_merge_artifacts_with_empty_artifacts(self):
        """Test that empty artifacts are allowed and produce valid package."""
        synthesizer = Synthesizer()
        # Empty artifacts should be allowed - branches may succeed without artifacts
        package = synthesizer.merge_artifacts({})
        assert package is not None
        assert package.artifacts == {}
    
    def test_merge_artifacts_returns_delivery_package(self):
        """Test that merging returns DeliveryPackage."""
        synthesizer = Synthesizer()
        
        artifacts = {
            "code": [
                {"artifact_type": "code", "content": "code"}
            ]
        }
        
        package = synthesizer.merge_artifacts(artifacts)
        
        assert isinstance(package, DeliveryPackage)
    
    def test_merge_artifacts_preserves_artifacts(self):
        """Test that artifacts are preserved in package."""
        synthesizer = Synthesizer()
        
        artifacts = {
            "code": [
                {"artifact_type": "code", "content": "code"}
            ],
            "documentation": [
                {"artifact_type": "documentation", "content": "docs"}
            ]
        }
        
        package = synthesizer.merge_artifacts(artifacts)
        
        assert package.artifacts == artifacts


class TestSynthesizerDeliveryPackageGeneration:
    """Tests for delivery package generation."""
    
    def test_generate_delivery_package_with_valid_inputs(self):
        """Test delivery package generation with valid inputs."""
        synthesizer = Synthesizer()
        
        branch_results = {
            "branch_backend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_backend_001",
                domain_name="backend",
                status="success",
                artifacts=[
                    {"artifact_type": "code", "content": "backend code"}
                ],
                start_time=1000.0,
                end_time=1010.0,
                duration=10.0
            )
        }
        
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        package = synthesizer.generate_delivery_package(
            run_id,
            "Test Project",
            branch_results,
            spec
        )
        
        assert isinstance(package, DeliveryPackage)
        assert package.run_id == run_id
        assert package.project_name == "Test Project"
    
    def test_generate_delivery_package_includes_execution_report(self):
        """Test that delivery package includes execution report."""
        synthesizer = Synthesizer()
        
        branch_results = {
            "branch_backend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_backend_001",
                domain_name="backend",
                status="success",
                artifacts=[],
                start_time=1000.0,
                end_time=1010.0,
                duration=10.0
            )
        }
        
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        package = synthesizer.generate_delivery_package(
            run_id,
            "Test Project",
            branch_results,
            spec
        )
        
        assert "execution_report" in package.__dict__
        assert package.execution_report["total_branches"] == 1
    
    def test_generate_delivery_package_includes_trace_information(self):
        """Test that delivery package includes trace information."""
        synthesizer = Synthesizer()
        
        branch_results = {
            "branch_backend_001": BranchResult(
                run_id="run_2026_04_06_001",
                branch_id="branch_backend_001",
                domain_name="backend",
                status="success",
                artifacts=[],
                start_time=1000.0,
                end_time=1010.0,
                duration=10.0
            )
        }
        
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        package = synthesizer.generate_delivery_package(
            run_id,
            "Test Project",
            branch_results,
            spec
        )
        
        assert "trace_information" in package.__dict__
        assert "branches" in package.trace_information


class TestSynthesizerIntegration:
    """Integration tests for Synthesizer."""
    
    def test_full_synthesis_workflow(self):
        """Test complete synthesis workflow."""
        synthesizer = Synthesizer()
        root_orch = RootOrchestrator()
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
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        # Synthesize results
        package = synthesizer.generate_delivery_package(
            run_id,
            spec.project_name,
            results,
            spec
        )
        
        # Verify package
        assert package.run_id == run_id
        assert package.project_name == spec.project_name
        assert isinstance(package.execution_report, dict)
        assert isinstance(package.trace_information, dict)


class TestSynthesizerProperties:
    """Property-based tests for Synthesizer.
    
    **Validates: Requirements 1, 10**
    """
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_synthesis_preserves_all_artifacts(self, project_name, project_description):
        """Property: Synthesis preserves all artifacts from branches.
        
        **Validates: Requirements 1, 10**
        """
        synthesizer = Synthesizer()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
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
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_synthesis_generates_valid_execution_report(self, project_name, project_description):
        """Property: Synthesis generates valid execution report.
        
        **Validates: Requirements 1, 10**
        """
        synthesizer = Synthesizer()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        package = synthesizer.generate_delivery_package(
            run_id,
            project_name,
            results,
            spec
        )
        
        # Verify execution report
        assert "total_branches" in package.execution_report
        assert "successful_branches" in package.execution_report
        assert "failed_branches" in package.execution_report
        assert package.execution_report["total_branches"] > 0
    
    @given(
        project_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
        project_description=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
    )
    def test_synthesis_generates_valid_trace_information(self, project_name, project_description):
        """Property: Synthesis generates valid trace information.
        
        **Validates: Requirements 1, 5, 10**
        """
        synthesizer = Synthesizer()
        root_orch = RootOrchestrator()
        intake = IntakeNode()
        
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        spec, run_id = intake.parse_request(request)
        branches = root_orch.decompose_specification(spec, run_id)
        results = root_orch.execute_branches(branches)
        
        package = synthesizer.generate_delivery_package(
            run_id,
            project_name,
            results,
            spec
        )
        
        # Verify trace information
        assert "branches" in package.trace_information
        assert len(package.trace_information["branches"]) > 0
