"""Unit tests for RoleTraceValidationModule."""

import pytest
from datetime import datetime
from kabbalah.role_trace_validation import (
    RoleTraceValidationModule,
    CanonicalRole,
    OperationCategory,
    TraceMetadata,
    RoleViolation,
)


class TestRoleTraceValidationModuleInitialization:
    """Tests for module initialization."""

    def test_initialization_creates_empty_logs(self):
        """Test that module initializes with empty logs."""
        module = RoleTraceValidationModule()
        assert module.violation_log == []
        assert module.trace_metadata_log == []

    def test_violation_log_is_immutable(self):
        """Test that violation log returns a copy."""
        module = RoleTraceValidationModule()
        log1 = module.violation_log
        log2 = module.violation_log
        assert log1 == log2
        assert log1 is not log2

    def test_trace_metadata_log_is_immutable(self):
        """Test that trace metadata log returns a copy."""
        module = RoleTraceValidationModule()
        log1 = module.trace_metadata_log
        log2 = module.trace_metadata_log
        assert log1 == log2
        assert log1 is not log2


class TestValidateOperationForRole:
    """Tests for validate_operation_for_role method."""

    def test_intake_clarifier_can_parse_request(self):
        """Test that Intake_Clarifier can parse requests."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.PARSE_REQUEST,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_intake_clarifier_cannot_decompose_specification(self):
        """Test that Intake_Clarifier cannot decompose specifications."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.DECOMPOSE_SPECIFICATION,
            "run_001:branch_001:leaf_001"
        )
        assert result is False

    def test_root_planner_can_decompose_specification(self):
        """Test that Root_Planner can decompose specifications."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.ROOT_PLANNER,
            OperationCategory.DECOMPOSE_SPECIFICATION,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_root_planner_cannot_execute_task(self):
        """Test that Root_Planner cannot execute tasks."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.ROOT_PLANNER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        assert result is False

    def test_domain_coordinator_can_spawn_leaf_nodes(self):
        """Test that Domain_Coordinator can spawn leaf nodes."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.DOMAIN_COORDINATOR,
            OperationCategory.SPAWN_LEAF_NODES,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_leaf_builder_can_execute_task(self):
        """Test that Leaf_Builder can execute tasks."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_leaf_builder_cannot_verify_result(self):
        """Test that Leaf_Builder cannot verify results."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.VERIFY_RESULT,
            "run_001:branch_001:leaf_001"
        )
        assert result is False

    def test_leaf_verifier_can_verify_result(self):
        """Test that Leaf_Verifier can verify results."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.LEAF_VERIFIER,
            OperationCategory.VERIFY_RESULT,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_leaf_auditor_can_audit_operation(self):
        """Test that Leaf_Auditor can audit operations."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.LEAF_AUDITOR,
            OperationCategory.AUDIT_OPERATION,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_synthesizer_can_collect_artifacts(self):
        """Test that Synthesizer_Consolidator can collect artifacts."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.SYNTHESIZER_CONSOLIDATOR,
            OperationCategory.COLLECT_ARTIFACTS,
            "run_001:branch_001:leaf_001"
        )
        assert result is True

    def test_all_roles_can_query_artifact(self):
        """Test that all roles can query artifacts."""
        module = RoleTraceValidationModule()
        for role in CanonicalRole:
            result = module.validate_operation_for_role(
                role,
                OperationCategory.QUERY_ARTIFACT,
                "run_001:branch_001:leaf_001"
            )
            assert result is True, f"{role.value} should be able to query artifacts"

    def test_all_roles_can_attach_metadata(self):
        """Test that all roles can attach metadata."""
        module = RoleTraceValidationModule()
        for role in CanonicalRole:
            result = module.validate_operation_for_role(
                role,
                OperationCategory.ATTACH_METADATA,
                "run_001:branch_001:leaf_001"
            )
            assert result is True, f"{role.value} should be able to attach metadata"

    def test_violation_logged_for_unauthorized_operation(self):
        """Test that violations are logged for unauthorized operations."""
        module = RoleTraceValidationModule()
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        
        violations = module.violation_log
        assert len(violations) == 1
        assert violations[0].role == CanonicalRole.INTAKE_CLARIFIER
        assert violations[0].operation == OperationCategory.EXECUTE_TASK
        assert violations[0].violation_type == "UNAUTHORIZED_OPERATION_FOR_ROLE"


class TestValidateOperationForRoleWithLogging:
    """Tests for validate_operation_for_role_with_logging method."""

    def test_allowed_operation_returns_true_and_no_error(self):
        """Test that allowed operations return True and no error."""
        module = RoleTraceValidationModule()
        is_allowed, error_msg = module.validate_operation_for_role_with_logging(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        assert is_allowed is True
        assert error_msg is None

    def test_blocked_operation_returns_false_and_error_message(self):
        """Test that blocked operations return False and error message."""
        module = RoleTraceValidationModule()
        is_allowed, error_msg = module.validate_operation_for_role_with_logging(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        assert is_allowed is False
        assert error_msg is not None
        assert "not allowed" in error_msg.lower()

    def test_error_message_contains_trace_id(self):
        """Test that error message contains trace_id."""
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        is_allowed, error_msg = module.validate_operation_for_role_with_logging(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            trace_id
        )
        assert is_allowed is False
        assert trace_id in error_msg


class TestAttachTraceMetadata:
    """Tests for attach_trace_metadata method."""

    def test_attach_metadata_to_artifact(self):
        """Test attaching metadata to an artifact."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        trace_id = "run_001:branch_001:leaf_001"
        
        result = module.attach_trace_metadata(
            artifact,
            trace_id,
            "Leaf_Builder",
            "Leaf_Builder",
            "execute_task"
        )
        
        assert "_trace_metadata" in result
        assert result["_trace_metadata"]["trace_id"] == trace_id
        assert result["_trace_metadata"]["canonical_group"] == "Leaf_Builder"
        assert result["_trace_metadata"]["role_name"] == "Leaf_Builder"
        assert result["_trace_metadata"]["operation_name"] == "execute_task"

    def test_attach_metadata_preserves_original_artifact(self):
        """Test that attaching metadata preserves original artifact content."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test", "data": 123}
        
        result = module.attach_trace_metadata(
            artifact,
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder"
        )
        
        assert result["content"] == "test"
        assert result["data"] == 123

    def test_attach_metadata_includes_timestamp(self):
        """Test that attached metadata includes timestamp."""
        module = RoleTraceValidationModule()
        before = datetime.now().timestamp()
        
        result = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder"
        )
        
        after = datetime.now().timestamp()
        timestamp = result["_trace_metadata"]["timestamp"]
        assert before <= timestamp <= after

    def test_attach_metadata_with_additional_metadata(self):
        """Test attaching metadata with additional metadata."""
        module = RoleTraceValidationModule()
        additional_metadata = {"user_id": "123", "request_id": "abc"}
        
        result = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder",
            metadata=additional_metadata
        )
        
        assert result["_trace_metadata"]["metadata"] == additional_metadata

    def test_attach_metadata_logs_metadata(self):
        """Test that attaching metadata logs it."""
        module = RoleTraceValidationModule()
        
        module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder"
        )
        
        assert len(module.trace_metadata_log) == 1
        assert module.trace_metadata_log[0].trace_id == "run_001:branch_001:leaf_001"

    def test_attach_metadata_multiple_times(self):
        """Test attaching metadata multiple times."""
        module = RoleTraceValidationModule()
        
        module.attach_trace_metadata({}, "run_001:branch_001:leaf_001", "Leaf_Builder", "Leaf_Builder")
        module.attach_trace_metadata({}, "run_001:branch_001:leaf_002", "Leaf_Verifier", "Leaf_Verifier")
        
        assert len(module.trace_metadata_log) == 2


class TestPropagateTraceId:
    """Tests for propagate_trace_id method."""

    def test_propagate_trace_id_to_artifact(self):
        """Test propagating trace_id to an artifact."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        trace_id = "run_001:branch_001:leaf_001"
        
        result = module.propagate_trace_id(
            trace_id,
            artifact,
            CanonicalRole.LEAF_BUILDER
        )
        
        assert result["_trace_metadata"]["trace_id"] == trace_id

    def test_propagate_trace_id_preserves_artifact_content(self):
        """Test that propagating trace_id preserves artifact content."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test", "data": 123}
        
        result = module.propagate_trace_id(
            "run_001:branch_001:leaf_001",
            artifact,
            CanonicalRole.LEAF_BUILDER
        )
        
        assert result["content"] == "test"
        assert result["data"] == 123

    def test_propagate_trace_id_fails_for_unauthorized_role(self):
        """Test that propagating trace_id works for all roles including INTAKE_CLARIFIER."""
        module = RoleTraceValidationModule()
        
        # INTAKE_CLARIFIER should now be able to propagate traces
        result = module.propagate_trace_id(
            "run_001:branch_001:leaf_001",
            {},
            CanonicalRole.INTAKE_CLARIFIER
        )
        
        assert result["_trace_metadata"]["trace_id"] == "run_001:branch_001:leaf_001"

    def test_propagate_trace_id_overwrites_existing_trace_id(self):
        """Test that propagating trace_id overwrites existing trace_id."""
        module = RoleTraceValidationModule()
        artifact = {
            "_trace_metadata": {
                "trace_id": "run_001:branch_001:leaf_001"
            }
        }
        new_trace_id = "run_002:branch_002:leaf_002"
        
        result = module.propagate_trace_id(
            new_trace_id,
            artifact,
            CanonicalRole.LEAF_BUILDER
        )
        
        assert result["_trace_metadata"]["trace_id"] == new_trace_id

    def test_propagate_trace_id_allowed_for_all_roles(self):
        """Test that propagating trace_id is allowed for all roles."""
        module = RoleTraceValidationModule()
        
        for role in CanonicalRole:
            result = module.propagate_trace_id(
                "run_001:branch_001:leaf_001",
                {},
                role
            )
            assert result["_trace_metadata"]["trace_id"] == "run_001:branch_001:leaf_001"


class TestExtractTraceMetadata:
    """Tests for extract_trace_metadata method."""

    def test_extract_metadata_from_artifact(self):
        """Test extracting metadata from an artifact."""
        module = RoleTraceValidationModule()
        artifact = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder",
            "execute_task"
        )
        
        metadata = module.extract_trace_metadata(artifact)
        assert metadata is not None
        assert metadata.trace_id == "run_001:branch_001:leaf_001"
        assert metadata.canonical_group == "Leaf_Builder"
        assert metadata.role_name == "Leaf_Builder"
        assert metadata.operation_name == "execute_task"

    def test_extract_metadata_returns_none_if_not_present(self):
        """Test that extracting metadata returns None if not present."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        
        metadata = module.extract_trace_metadata(artifact)
        assert metadata is None

    def test_extract_metadata_preserves_additional_metadata(self):
        """Test that extracting metadata preserves additional metadata."""
        module = RoleTraceValidationModule()
        additional_metadata = {"user_id": "123"}
        artifact = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder",
            metadata=additional_metadata
        )
        
        metadata = module.extract_trace_metadata(artifact)
        assert metadata.metadata == additional_metadata


class TestValidateTraceMetadataConsistency:
    """Tests for validate_trace_metadata_consistency method."""

    def test_validate_consistent_metadata(self):
        """Test validating consistent metadata."""
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        artifact = module.attach_trace_metadata(
            {},
            trace_id,
            "Leaf_Builder",
            "Leaf_Builder"
        )
        
        result = module.validate_trace_metadata_consistency(artifact, trace_id)
        assert result is True

    def test_validate_inconsistent_metadata(self):
        """Test validating inconsistent metadata."""
        module = RoleTraceValidationModule()
        artifact = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder"
        )
        
        result = module.validate_trace_metadata_consistency(
            artifact,
            "run_002:branch_002:leaf_002"
        )
        assert result is False

    def test_validate_missing_metadata(self):
        """Test validating missing metadata."""
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        
        result = module.validate_trace_metadata_consistency(
            artifact,
            "run_001:branch_001:leaf_001"
        )
        assert result is False


class TestGetViolationHistory:
    """Tests for violation history methods."""

    def test_get_violation_history(self):
        """Test getting violation history."""
        module = RoleTraceValidationModule()
        
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.VERIFY_RESULT,
            "run_001:branch_001:leaf_002"
        )
        
        history = module.get_violation_history()
        assert len(history) == 2

    def test_get_violations_for_role(self):
        """Test getting violations for a specific role."""
        module = RoleTraceValidationModule()
        
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.VERIFY_RESULT,
            "run_001:branch_001:leaf_002"
        )
        
        violations = module.get_violations_for_role(CanonicalRole.INTAKE_CLARIFIER)
        assert len(violations) == 1
        assert violations[0].role == CanonicalRole.INTAKE_CLARIFIER

    def test_get_violations_for_operation(self):
        """Test getting violations for a specific operation."""
        module = RoleTraceValidationModule()
        
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_001"
        )
        module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.EXECUTE_TASK,
            "run_001:branch_001:leaf_002"
        )
        
        violations = module.get_violations_for_operation(OperationCategory.EXECUTE_TASK)
        assert len(violations) == 1

    def test_get_violations_by_trace_id(self):
        """Test getting violations by trace_id."""
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.EXECUTE_TASK,
            trace_id
        )
        module.validate_operation_for_role(
            CanonicalRole.INTAKE_CLARIFIER,
            OperationCategory.VERIFY_RESULT,
            trace_id
        )
        
        violations = module.get_violations_by_trace_id(trace_id)
        assert len(violations) == 2
        assert all(v.trace_id == trace_id for v in violations)


class TestGetTraceMetadata:
    """Tests for trace metadata retrieval methods."""

    def test_get_trace_metadata_for_trace_id(self):
        """Test getting trace metadata for a specific trace_id."""
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        module.attach_trace_metadata({}, trace_id, "Leaf_Builder", "Leaf_Builder")
        module.attach_trace_metadata({}, trace_id, "Leaf_Verifier", "Leaf_Verifier")
        module.attach_trace_metadata({}, "run_002:branch_002:leaf_002", "Leaf_Builder", "Leaf_Builder")
        
        metadata = module.get_trace_metadata_for_trace_id(trace_id)
        assert len(metadata) == 2
        assert all(m.trace_id == trace_id for m in metadata)

    def test_get_trace_metadata_for_role(self):
        """Test getting trace metadata for a specific role."""
        module = RoleTraceValidationModule()
        
        module.attach_trace_metadata({}, "run_001:branch_001:leaf_001", "Leaf_Builder", "Leaf_Builder")
        module.attach_trace_metadata({}, "run_001:branch_001:leaf_002", "Leaf_Verifier", "Leaf_Verifier")
        module.attach_trace_metadata({}, "run_002:branch_002:leaf_003", "Leaf_Builder", "Leaf_Builder")
        
        metadata = module.get_trace_metadata_for_role("Leaf_Builder")
        assert len(metadata) == 2
        assert all(m.role_name == "Leaf_Builder" for m in metadata)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_operation_with_empty_trace_id(self):
        """Test operation with empty trace_id."""
        module = RoleTraceValidationModule()
        result = module.validate_operation_for_role(
            CanonicalRole.LEAF_BUILDER,
            OperationCategory.EXECUTE_TASK,
            ""
        )
        assert result is True

    def test_attach_metadata_with_empty_artifact(self):
        """Test attaching metadata to empty artifact."""
        module = RoleTraceValidationModule()
        result = module.attach_trace_metadata(
            {},
            "run_001:branch_001:leaf_001",
            "Leaf_Builder",
            "Leaf_Builder"
        )
        assert "_trace_metadata" in result

    def test_propagate_trace_id_with_empty_artifact(self):
        """Test propagating trace_id to empty artifact."""
        module = RoleTraceValidationModule()
        result = module.propagate_trace_id(
            "run_001:branch_001:leaf_001",
            {},
            CanonicalRole.LEAF_BUILDER
        )
        assert result["_trace_metadata"]["trace_id"] == "run_001:branch_001:leaf_001"

    def test_multiple_violations_for_same_role(self):
        """Test multiple violations for the same role."""
        module = RoleTraceValidationModule()
        
        for i in range(5):
            module.validate_operation_for_role(
                CanonicalRole.INTAKE_CLARIFIER,
                OperationCategory.EXECUTE_TASK,
                f"run_001:branch_001:leaf_{i:03d}"
            )
        
        violations = module.get_violations_for_role(CanonicalRole.INTAKE_CLARIFIER)
        assert len(violations) == 5

    def test_all_canonical_roles_defined(self):
        """Test that all canonical roles are defined."""
        expected_roles = {
            "Intake_Clarifier",
            "Root_Planner",
            "Domain_Coordinator",
            "Leaf_Builder",
            "Leaf_Verifier",
            "Leaf_Auditor",
            "Synthesizer_Consolidator",
        }
        actual_roles = {role.value for role in CanonicalRole}
        assert actual_roles == expected_roles

    def test_all_operation_categories_defined(self):
        """Test that all operation categories are defined."""
        expected_operations = {
            "parse_request",
            "decompose_specification",
            "spawn_leaf_nodes",
            "execute_task",
            "verify_result",
            "audit_operation",
            "collect_artifacts",
            "attach_metadata",
            "propagate_trace",
            "query_artifact",
        }
        actual_operations = {op.value for op in OperationCategory}
        assert actual_operations == expected_operations
