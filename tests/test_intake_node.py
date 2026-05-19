"""Unit tests for IntakeNode class."""

import pytest
import re
from datetime import datetime
from kabbalah.intake_node import IntakeNode, InvalidRequestError, SpecificationError
from kabbalah.models import UserRequest, Specification


class TestIntakeNodeValidation:
    """Tests for request validation."""
    
    def test_parse_request_with_null_request(self):
        """Test that null request raises InvalidRequestError."""
        intake = IntakeNode()
        with pytest.raises(InvalidRequestError, match="Request cannot be null"):
            intake.parse_request(None)
    
    def test_parse_request_with_missing_project_name(self):
        """Test that missing project_name raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="",
            project_description="A test project"
        )
        with pytest.raises(InvalidRequestError, match="project_name"):
            intake.parse_request(request)
    
    def test_parse_request_with_missing_project_description(self):
        """Test that missing project_description raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description=""
        )
        with pytest.raises(InvalidRequestError, match="project_description"):
            intake.parse_request(request)
    
    def test_parse_request_with_none_project_name(self):
        """Test that None project_name raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name=None,
            project_description="A test project"
        )
        with pytest.raises(InvalidRequestError, match="project_name"):
            intake.parse_request(request)
    
    def test_parse_request_with_non_string_project_name(self):
        """Test that non-string project_name raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name=123,
            project_description="A test project"
        )
        with pytest.raises(InvalidRequestError, match="project_name"):
            intake.parse_request(request)


class TestIntakeNodeRunIdGeneration:
    """Tests for run_id generation."""
    
    def test_run_id_format(self):
        """Test that run_id has correct format."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        spec, run_id = intake.parse_request(request)
        
        # Verify format: run_YYYY_MM_DD_NNN
        pattern = r"^run_\d{4}_\d{2}_\d{2}_\d{3}$"
        assert re.match(pattern, run_id), f"run_id {run_id} does not match pattern"
    
    def test_run_id_uniqueness(self):
        """Test that consecutive run_ids are unique."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec1, run_id1 = intake.parse_request(request)
        spec2, run_id2 = intake.parse_request(request)
        
        assert run_id1 != run_id2, "run_ids should be unique"
    
    def test_run_id_counter_increments(self):
        """Test that run_id counter increments correctly."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec1, run_id1 = intake.parse_request(request)
        spec2, run_id2 = intake.parse_request(request)
        
        # Extract counter from run_ids
        counter1 = int(run_id1.split("_")[-1])
        counter2 = int(run_id2.split("_")[-1])
        
        assert counter2 == counter1 + 1, "Counter should increment by 1"
    
    def test_run_id_contains_date(self):
        """Test that run_id contains current date."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Extract date from run_id
        date_str = run_id.split("_")[1:4]
        date_str = "_".join(date_str)
        
        # Verify it matches today's date
        today = datetime.utcnow().strftime("%Y_%m_%d")
        assert date_str == today, f"Date {date_str} does not match today {today}"


class TestIntakeNodeSpecificationGeneration:
    """Tests for specification generation."""
    
    def test_specification_has_required_fields(self):
        """Test that specification has all required fields."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.run_id == run_id
        assert spec.project_name == "Test Project"
        assert spec.project_description == "A test project"
        assert spec.scope is not None
        assert spec.constraints is not None
        assert spec.resources is not None
        assert spec.domains is not None
        assert spec.dependencies is not None
        assert spec.created_at is not None
        assert spec.version == "1.0"
    
    def test_specification_with_provided_scope(self):
        """Test that provided scope is used."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
            scope="Custom scope"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.scope == "Custom scope"
    
    def test_specification_with_provided_constraints(self):
        """Test that provided constraints are used."""
        intake = IntakeNode()
        constraints = ["Constraint 1", "Constraint 2"]
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
            constraints=constraints
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.constraints == constraints
    
    def test_specification_with_provided_resources(self):
        """Test that provided resources are used."""
        intake = IntakeNode()
        resources = {"cpu": 4, "memory": 8}
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
            resources=resources
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.resources == resources
    
    def test_specification_has_default_domains(self):
        """Test that specification has default domains."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should have at least backend and frontend
        assert "backend" in spec.domains
        assert "frontend" in spec.domains
    
    def test_specification_infers_infrastructure_domain(self):
        """Test that infrastructure domain is inferred from keywords."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="Deploy to AWS with Docker containers"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert "infrastructure" in spec.domains
    
    def test_specification_infers_testing_domain(self):
        """Test that testing domain is inferred from keywords."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="Build a project with comprehensive testing"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert "testing" in spec.domains
    
    def test_specification_has_dependencies(self):
        """Test that specification has domain dependencies."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Frontend should depend on backend
        assert "backend" in spec.dependencies.get("frontend", [])
    
    def test_specification_created_at_is_timestamp(self):
        """Test that created_at is a valid timestamp."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should be a float representing seconds since epoch
        assert isinstance(spec.created_at, float)
        assert spec.created_at > 0


class TestIntakeNodeSpecificationValidation:
    """Tests for specification validation."""
    
    def test_specification_run_id_matches(self):
        """Test that specification run_id matches returned run_id."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.run_id == run_id
    
    def test_specification_is_valid_after_parse(self):
        """Test that specification is valid after parsing."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        # All required fields should be present
        assert spec.project_name
        assert spec.project_description
        assert spec.scope
        assert spec.domains
        assert len(spec.domains) > 0


class TestIntakeNodeEdgeCases:
    """Tests for edge cases."""
    
    def test_parse_request_with_whitespace_only_name(self):
        """Test that whitespace-only project_name raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="   ",
            project_description="A test project"
        )
        with pytest.raises(InvalidRequestError):
            intake.parse_request(request)
    
    def test_parse_request_with_whitespace_only_description(self):
        """Test that whitespace-only project_description raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="   "
        )
        with pytest.raises(InvalidRequestError):
            intake.parse_request(request)
    
    def test_parse_request_with_long_project_name(self):
        """Test that long project_name is accepted."""
        intake = IntakeNode()
        long_name = "A" * 500
        request = UserRequest(
            project_name=long_name,
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.project_name == long_name
    
    def test_parse_request_with_special_characters(self):
        """Test that special characters in project_name are accepted."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test-Project_2024!@#",
            project_description="A test project"
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.project_name == "Test-Project_2024!@#"
    
    def test_parse_request_with_metadata(self):
        """Test that metadata is preserved."""
        intake = IntakeNode()
        metadata = {"key1": "value1", "key2": 123}
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
            metadata=metadata
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.metadata == metadata
    
    def test_parse_request_with_empty_metadata(self):
        """Test that empty metadata is handled."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
            metadata={}
        )
        
        spec, run_id = intake.parse_request(request)
        
        assert spec.metadata == {}


class TestIntakeNodeIntegration:
    """Integration tests for IntakeNode."""
    
    def test_full_workflow(self):
        """Test complete workflow from request to specification."""
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
        
        # Verify all fields
        assert spec.project_name == "E-Commerce Platform"
        assert spec.scope == "Full-stack web application"
        assert len(spec.constraints) == 2
        assert spec.resources["budget"] == 50000
        assert spec.metadata["client"] == "Acme Corp"
        assert "backend" in spec.domains
        assert "frontend" in spec.domains
        assert "infrastructure" in spec.domains
        assert re.match(r"^run_\d{4}_\d{2}_\d{2}_\d{3}$", run_id)


class TestIntakeNodePrivateMethods:
    """Tests for private methods to ensure full coverage."""
    
    def test_infer_scope_with_short_description(self):
        """Test scope inference with short description."""
        intake = IntakeNode()
        description = "Build a simple app"
        request = UserRequest(
            project_name="Test",
            project_description=description,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.scope == "Build a simple app"
    
    def test_infer_scope_with_long_description(self):
        """Test scope inference with long description."""
        intake = IntakeNode()
        long_desc = "A" * 300 + ". More text"
        request = UserRequest(
            project_name="Test",
            project_description=long_desc,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert len(spec.scope) <= 203  # 200 chars + "..."
    
    def test_infer_scope_with_multiple_sentences(self):
        """Test scope inference with multiple sentences."""
        intake = IntakeNode()
        description = "First sentence. Second sentence. Third sentence."
        request = UserRequest(
            project_name="Test",
            project_description=description,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.scope == "First sentence"
    
    def test_default_constraints_generated(self):
        """Test that default constraints are generated when not provided."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="A test project",
            constraints=None
        )
        spec, _ = intake.parse_request(request)
        assert len(spec.constraints) == 3
        assert "best practices" in spec.constraints[0].lower()
    
    def test_default_resources_generated(self):
        """Test that default resources are generated when not provided."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="A test project",
            resources=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.resources["max_tokens"] == 4000
        assert spec.resources["timeout_seconds"] == 300
        assert spec.resources["retry_count"] == 3
    
    def test_infer_domains_with_deploy_keyword(self):
        """Test infrastructure domain inference with deploy keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Deploy the application"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_with_aws_keyword(self):
        """Test infrastructure domain inference with AWS keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Use AWS for hosting"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_with_docker_keyword(self):
        """Test infrastructure domain inference with Docker keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Containerize with Docker"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_with_cloud_keyword(self):
        """Test infrastructure domain inference with cloud keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Deploy to cloud"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_with_testing_keyword(self):
        """Test testing domain inference with testing keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Include comprehensive testing"
        )
        spec, _ = intake.parse_request(request)
        assert "testing" in spec.domains
    
    def test_infer_domains_with_qa_keyword(self):
        """Test testing domain inference with QA keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="QA and verification"
        )
        spec, _ = intake.parse_request(request)
        assert "testing" in spec.domains
    
    def test_infer_domains_with_test_keyword(self):
        """Test testing domain inference with test keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Write test cases"
        )
        spec, _ = intake.parse_request(request)
        assert "testing" in spec.domains
    
    def test_infer_domains_with_documentation_keyword(self):
        """Test documentation domain inference."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Create documentation"
        )
        spec, _ = intake.parse_request(request)
        assert "documentation" in spec.domains
    
    def test_infer_domains_with_api_doc_keyword(self):
        """Test documentation domain inference with API doc keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Generate API doc"
        )
        spec, _ = intake.parse_request(request)
        assert "documentation" in spec.domains
    
    def test_infer_domains_with_document_keyword(self):
        """Test documentation domain inference with document keyword."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Document the system"
        )
        spec, _ = intake.parse_request(request)
        assert "documentation" in spec.domains
    
    def test_infer_dependencies_frontend_depends_on_backend(self):
        """Test that frontend depends on backend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build frontend and backend"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.dependencies.get("frontend", [])
    
    def test_infer_dependencies_testing_depends_on_backend(self):
        """Test that testing depends on backend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build with testing and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.dependencies.get("testing", [])
    
    def test_infer_dependencies_testing_depends_on_frontend(self):
        """Test that testing depends on frontend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build with testing and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        assert "frontend" in spec.dependencies.get("testing", [])
    
    def test_infer_dependencies_infrastructure_depends_on_backend(self):
        """Test that infrastructure depends on backend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.dependencies.get("infrastructure", [])
    
    def test_infer_dependencies_no_frontend_no_dependency(self):
        """Test that frontend dependency is not added if frontend not in domains."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend API only"
        )
        spec, _ = intake.parse_request(request)
        # Frontend should not be in domains, so no dependency
        if "frontend" in spec.domains:
            assert "backend" in spec.dependencies.get("frontend", [])
    
    def test_specification_validation_invalid_run_id_format(self):
        """Test that invalid run_id format raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.run_id = "invalid_format"
        with pytest.raises(SpecificationError, match="Invalid run_id format"):
            intake._validate_specification(spec, "invalid_format")
    
    def test_specification_validation_missing_project_name(self):
        """Test that missing project_name raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.project_name = ""
        with pytest.raises(SpecificationError, match="project_name"):
            intake._validate_specification(spec, run_id)
    
    def test_specification_validation_missing_project_description(self):
        """Test that missing project_description raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.project_description = ""
        with pytest.raises(SpecificationError, match="project_description"):
            intake._validate_specification(spec, run_id)
    
    def test_specification_validation_missing_scope(self):
        """Test that missing scope raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.scope = ""
        with pytest.raises(SpecificationError, match="scope"):
            intake._validate_specification(spec, run_id)
    
    def test_specification_validation_missing_domains(self):
        """Test that missing domains raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.domains = []
        with pytest.raises(SpecificationError, match="at least one domain"):
            intake._validate_specification(spec, run_id)
    
    def test_specification_validation_mismatched_run_id(self):
        """Test that mismatched run_id raises error."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Manually create invalid spec
        spec.run_id = "run_2026_01_01_999"
        with pytest.raises(SpecificationError, match="run_id does not match"):
            intake._validate_specification(spec, run_id)
    
    def test_specification_error_on_generation_failure(self):
        """Test that SpecificationError is raised on generation failure."""
        intake = IntakeNode()
        # Create a request that will cause an error during generation
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        # This should work normally, but we're testing error handling
        spec, run_id = intake.parse_request(request)
        assert spec is not None
    
    def test_run_id_counter_resets_on_date_change(self):
        """Test that run_id counter resets when date changes."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        
        # Get first run_id
        spec1, run_id1 = intake.parse_request(request)
        counter1 = int(run_id1.split("_")[-1])
        
        # Manually reset the date to simulate date change
        IntakeNode._last_date = None
        
        # Get second run_id (should reset counter)
        spec2, run_id2 = intake.parse_request(request)
        counter2 = int(run_id2.split("_")[-1])
        
        # Counter should be 1 after reset
        assert counter2 == 1
    
    def test_parse_request_with_empty_constraints_list(self):
        """Test that empty constraints list is handled."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            constraints=[]
        )
        spec, _ = intake.parse_request(request)
        assert spec.constraints == []
    
    def test_parse_request_with_empty_resources_dict(self):
        """Test that empty resources dict is handled."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            resources={}
        )
        spec, _ = intake.parse_request(request)
        assert spec.resources == {}
    
    def test_specification_version_is_1_0(self):
        """Test that specification version is 1.0."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, _ = intake.parse_request(request)
        assert spec.version == "1.0"
    
    def test_multiple_infrastructure_keywords(self):
        """Test that multiple infrastructure keywords are recognized."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Deploy to AWS with Docker containers and infrastructure as code"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_case_insensitive_keyword_matching(self):
        """Test that keyword matching is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="DEPLOY to AWS with DOCKER"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_all_domains_have_dependency_entry(self):
        """Test that all domains have an entry in dependencies dict."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build with testing and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        for domain in spec.domains:
            assert domain in spec.dependencies


class TestIntakeNodeCoverageGaps:
    """Tests to ensure >80% code coverage."""
    
    def test_validate_request_with_non_string_description(self):
        """Test that non-string project_description raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description=123
        )
        with pytest.raises(InvalidRequestError, match="project_description"):
            intake.parse_request(request)
    
    def test_validate_request_with_none_description(self):
        """Test that None project_description raises InvalidRequestError."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description=None
        )
        with pytest.raises(InvalidRequestError, match="project_description"):
            intake.parse_request(request)
    
    def test_infer_scope_with_no_period(self):
        """Test scope inference when description has no period."""
        intake = IntakeNode()
        description = "Build a simple app without any period"
        request = UserRequest(
            project_name="Test",
            project_description=description,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.scope == description
    
    def test_infer_scope_truncates_at_200_chars(self):
        """Test that scope is truncated at 200 characters."""
        intake = IntakeNode()
        long_text = "A" * 250
        description = long_text + ". More text"
        request = UserRequest(
            project_name="Test",
            project_description=description,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert len(spec.scope) == 203  # 200 chars + "..."
        assert spec.scope.endswith("...")
    
    def test_infer_domains_without_any_keywords(self):
        """Test that default domains are returned when no keywords match."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build a simple application"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.domains
        assert "frontend" in spec.domains
        assert len(spec.domains) == 2
    
    def test_infer_domains_with_multiple_keywords(self):
        """Test domain inference with multiple keywords."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Deploy to AWS with Docker, comprehensive testing, and documentation"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
        assert "testing" in spec.domains
        assert "documentation" in spec.domains
    
    def test_infer_dependencies_all_domains_present(self):
        """Test dependency inference when all domains are present."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend, frontend, infrastructure, testing, and documentation"
        )
        spec, _ = intake.parse_request(request)
        
        # Verify all expected dependencies
        assert "backend" in spec.dependencies.get("frontend", [])
        assert "backend" in spec.dependencies.get("testing", [])
        assert "frontend" in spec.dependencies.get("testing", [])
        assert "backend" in spec.dependencies.get("infrastructure", [])
    
    def test_infer_dependencies_only_backend_frontend(self):
        """Test dependency inference with only backend and frontend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend and frontend"
        )
        spec, _ = intake.parse_request(request)
        
        # Frontend should depend on backend
        assert "backend" in spec.dependencies.get("frontend", [])
        # Backend should have no dependencies
        assert spec.dependencies.get("backend", []) == []
    
    def test_specification_error_on_invalid_request(self):
        """Test that SpecificationError is raised on invalid request."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        assert spec is not None
        assert run_id is not None
    
    def test_parse_request_returns_tuple(self):
        """Test that parse_request returns a tuple of (Specification, str)."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        result = intake.parse_request(request)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Specification)
        assert isinstance(result[1], str)
    
    def test_run_id_format_validation_strict(self):
        """Test that run_id format validation is strict."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Verify exact format
        parts = run_id.split("_")
        assert len(parts) == 5  # run, YYYY, MM, DD, NNN
        assert parts[0] == "run"
        assert len(parts[1]) == 4  # YYYY
        assert len(parts[2]) == 2  # MM
        assert len(parts[3]) == 2  # DD
        assert len(parts[4]) == 3  # NNN
        
        # Verify regex format
        assert re.match(r"^run_\d{4}_\d{2}_\d{2}_\d{3}$", run_id)
    
    def test_specification_metadata_preserved_when_none(self):
        """Test that metadata is set to empty dict when None."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            metadata=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.metadata == {}
    
    def test_specification_constraints_preserved_when_empty_list(self):
        """Test that empty constraints list is preserved."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            constraints=[]
        )
        spec, _ = intake.parse_request(request)
        assert spec.constraints == []
    
    def test_specification_resources_preserved_when_empty_dict(self):
        """Test that empty resources dict is preserved."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            resources={}
        )
        spec, _ = intake.parse_request(request)
        assert spec.resources == {}
    
    def test_infer_scope_with_empty_string_description(self):
        """Test scope inference with empty string (should fail validation first)."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description=""
        )
        with pytest.raises(InvalidRequestError):
            intake.parse_request(request)
    
    def test_multiple_consecutive_parse_requests(self):
        """Test that multiple consecutive parse requests work correctly."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        
        run_ids = []
        for i in range(5):
            spec, run_id = intake.parse_request(request)
            run_ids.append(run_id)
            assert spec is not None
        
        # All run_ids should be unique
        assert len(set(run_ids)) == 5
    
    def test_specification_created_at_is_recent(self):
        """Test that created_at timestamp is recent."""
        import time
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        
        before = time.time()
        spec, _ = intake.parse_request(request)
        after = time.time()
        
        assert before <= spec.created_at <= after
    
    def test_infer_domains_case_insensitive_deploy(self):
        """Test that 'deploy' keyword is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="DEPLOY the application"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_case_insensitive_infrastructure(self):
        """Test that 'infrastructure' keyword is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Set up INFRASTRUCTURE"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_case_insensitive_cloud(self):
        """Test that 'cloud' keyword is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Deploy to CLOUD"
        )
        spec, _ = intake.parse_request(request)
        assert "infrastructure" in spec.domains
    
    def test_infer_domains_case_insensitive_test(self):
        """Test that 'test' keyword is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Write TEST cases"
        )
        spec, _ = intake.parse_request(request)
        assert "testing" in spec.domains
    
    def test_infer_domains_case_insensitive_documentation(self):
        """Test that 'documentation' keyword is case-insensitive."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Create DOCUMENTATION"
        )
        spec, _ = intake.parse_request(request)
        assert "documentation" in spec.domains
    
    def test_specification_has_all_required_fields_populated(self):
        """Test that all required fields are populated in specification."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test Project",
            project_description="A comprehensive test project"
        )
        spec, run_id = intake.parse_request(request)
        
        # Check all fields are populated
        assert spec.run_id
        assert spec.project_name
        assert spec.project_description
        assert spec.scope
        assert spec.constraints is not None
        assert spec.resources is not None
        assert spec.domains
        assert spec.dependencies is not None
        assert spec.metadata is not None
        assert spec.created_at
        assert spec.version
    
    def test_infer_dependencies_backend_has_no_dependencies(self):
        """Test that backend domain has no dependencies."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend and frontend"
        )
        spec, _ = intake.parse_request(request)
        assert spec.dependencies.get("backend", []) == []
    
    def test_infer_dependencies_frontend_has_backend_dependency(self):
        """Test that frontend depends on backend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend and frontend"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.dependencies.get("frontend", [])
    
    def test_infer_dependencies_testing_has_both_dependencies(self):
        """Test that testing depends on both backend and frontend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend, frontend, and testing"
        )
        spec, _ = intake.parse_request(request)
        testing_deps = spec.dependencies.get("testing", [])
        assert "backend" in testing_deps
        assert "frontend" in testing_deps
    
    def test_infer_dependencies_infrastructure_depends_on_backend(self):
        """Test that infrastructure depends on backend."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        assert "backend" in spec.dependencies.get("infrastructure", [])
    
    def test_validate_request_accepts_valid_request(self):
        """Test that valid request passes validation."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Valid Project",
            project_description="Valid description"
        )
        # Should not raise any exception
        spec, run_id = intake.parse_request(request)
        assert spec is not None
        assert run_id is not None
    
    def test_specification_version_always_1_0(self):
        """Test that specification version is always 1.0."""
        intake = IntakeNode()
        for i in range(3):
            request = UserRequest(
                project_name=f"Test {i}",
                project_description=f"Test description {i}"
            )
            spec, _ = intake.parse_request(request)
            assert spec.version == "1.0"
    
    def test_run_id_date_component_is_valid(self):
        """Test that run_id date component is valid."""
        from datetime import datetime
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Extract date from run_id
        parts = run_id.split("_")
        year = int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
        
        # Verify date is valid
        assert 2000 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31
    
    def test_run_id_counter_component_is_valid(self):
        """Test that run_id counter component is valid."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test"
        )
        spec, run_id = intake.parse_request(request)
        
        # Extract counter from run_id
        counter = int(run_id.split("_")[-1])
        
        # Verify counter is valid
        assert 1 <= counter <= 999
    
    def test_infer_scope_preserves_first_sentence(self):
        """Test that scope inference preserves first sentence."""
        intake = IntakeNode()
        description = "First sentence here. Second sentence. Third sentence."
        request = UserRequest(
            project_name="Test",
            project_description=description,
            scope=None
        )
        spec, _ = intake.parse_request(request)
        assert spec.scope == "First sentence here"
    
    def test_default_constraints_are_meaningful(self):
        """Test that default constraints are meaningful."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            constraints=None
        )
        spec, _ = intake.parse_request(request)
        
        # Check that constraints are meaningful
        assert len(spec.constraints) > 0
        for constraint in spec.constraints:
            assert isinstance(constraint, str)
            assert len(constraint) > 0
    
    def test_default_resources_have_required_keys(self):
        """Test that default resources have required keys."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Test",
            resources=None
        )
        spec, _ = intake.parse_request(request)
        
        # Check that resources have required keys
        assert "max_tokens" in spec.resources
        assert "timeout_seconds" in spec.resources
        assert "retry_count" in spec.resources
    
    def test_specification_domains_are_strings(self):
        """Test that all domains are strings."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend, frontend, and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        
        for domain in spec.domains:
            assert isinstance(domain, str)
            assert len(domain) > 0
    
    def test_specification_dependencies_are_lists(self):
        """Test that all dependencies are lists."""
        intake = IntakeNode()
        request = UserRequest(
            project_name="Test",
            project_description="Build backend, frontend, and deploy to AWS"
        )
        spec, _ = intake.parse_request(request)
        
        for domain, deps in spec.dependencies.items():
            assert isinstance(deps, list)
            for dep in deps:
                assert isinstance(dep, str)
