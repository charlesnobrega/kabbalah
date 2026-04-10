"""Property-based tests for RoleTraceValidationModule.

These tests validate core properties of the role trace validation system:
- Property 12: Role validation consistency
- Property 13: Trace metadata attachment
- Property 14: Trace propagation
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime
from kabbalah.role_trace_validation import (
    RoleTraceValidationModule,
    CanonicalRole,
    OperationCategory,
)


class TestRoleValidationProperties:
    """Property-based tests for role validation.
    
    **Validates: Requirements 3.2**
    """

    @given(
        role=st.sampled_from(list(CanonicalRole)),
        operation=st.sampled_from(list(OperationCategory))
    )
    def test_role_validation_is_deterministic(self, role, operation):
        """Property: Role validation is deterministic.
        
        For the same role and operation, validation result should always be the same.
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        result1 = module.validate_operation_for_role(role, operation, trace_id)
        result2 = module.validate_operation_for_role(role, operation, trace_id)
        
        assert result1 == result2

    @given(
        role=st.sampled_from(list(CanonicalRole)),
        operation=st.sampled_from(list(OperationCategory))
    )
    def test_unauthorized_operations_logged_as_violations(self, role, operation):
        """Property: Unauthorized operations are logged as violations.
        
        If an operation is not allowed for a role, it must be logged as a violation.
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        is_allowed = module.validate_operation_for_role(role, operation, trace_id)
        violations = module.get_violations_for_role(role)
        
        if not is_allowed:
            # Should have at least one violation
            assert len(violations) > 0
            # The violation should be for this operation
            assert any(v.operation == operation for v in violations)
        else:
            # If allowed, no violation should be logged
            assert not any(v.operation == operation for v in violations)

    @given(
        role=st.sampled_from(list(CanonicalRole)),
        operation=st.sampled_from(list(OperationCategory))
    )
    def test_violation_contains_required_fields(self, role, operation):
        """Property: Violations contain all required fields.
        
        Each violation must contain: role, operation, trace_id, timestamp, violation_type, message
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        module.validate_operation_for_role(role, operation, trace_id)
        violations = module.get_violations_for_role(role)
        
        for violation in violations:
            assert violation.role is not None
            assert violation.operation is not None
            assert violation.trace_id is not None
            assert violation.timestamp > 0
            assert violation.violation_type is not None
            assert len(violation.violation_type) > 0
            assert violation.message is not None
            assert len(violation.message) > 0

    @given(
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_all_roles_can_query_artifacts(self, role):
        """Property: All roles can query artifacts.
        
        The QUERY_ARTIFACT operation must be allowed for all roles.
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        result = module.validate_operation_for_role(
            role,
            OperationCategory.QUERY_ARTIFACT,
            trace_id
        )
        
        assert result is True

    @given(
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_all_roles_can_attach_metadata(self, role):
        """Property: All roles can attach metadata.
        
        The ATTACH_METADATA operation must be allowed for all roles.
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        result = module.validate_operation_for_role(
            role,
            OperationCategory.ATTACH_METADATA,
            trace_id
        )
        
        assert result is True

    @given(
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_all_roles_can_propagate_trace(self, role):
        """Property: All roles can propagate trace_id.
        
        The PROPAGATE_TRACE operation must be allowed for all roles.
        """
        module = RoleTraceValidationModule()
        trace_id = "run_001:branch_001:leaf_001"
        
        result = module.validate_operation_for_role(
            role,
            OperationCategory.PROPAGATE_TRACE,
            trace_id
        )
        
        assert result is True

    def test_intake_clarifier_permissions(self):
        """Property: Intake_Clarifier has correct permissions.
        
        Intake_Clarifier can: parse_request, query_artifact, attach_metadata
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.INTAKE_CLARIFIER
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.PARSE_REQUEST, trace_id)
        assert module.validate_operation_for_role(role, OperationCategory.QUERY_ARTIFACT, trace_id)
        assert module.validate_operation_for_role(role, OperationCategory.ATTACH_METADATA, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        assert not module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)

    def test_root_planner_permissions(self):
        """Property: Root_Planner has correct permissions.
        
        Root_Planner can: decompose_specification, spawn_leaf_nodes, query_artifact, attach_metadata, propagate_trace
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.ROOT_PLANNER
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.DECOMPOSE_SPECIFICATION, trace_id)
        assert module.validate_operation_for_role(role, OperationCategory.SPAWN_LEAF_NODES, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        assert not module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)

    def test_leaf_builder_permissions(self):
        """Property: Leaf_Builder has correct permissions.
        
        Leaf_Builder can: execute_task, attach_metadata, propagate_trace, query_artifact
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.LEAF_BUILDER
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)
        assert not module.validate_operation_for_role(role, OperationCategory.AUDIT_OPERATION, trace_id)

    def test_leaf_verifier_permissions(self):
        """Property: Leaf_Verifier has correct permissions.
        
        Leaf_Verifier can: verify_result, execute_task, query_artifact, attach_metadata, propagate_trace
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.LEAF_VERIFIER
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)
        assert module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.AUDIT_OPERATION, trace_id)

    def test_leaf_auditor_permissions(self):
        """Property: Leaf_Auditor has correct permissions.
        
        Leaf_Auditor can: audit_operation, query_artifact, attach_metadata, propagate_trace
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.LEAF_AUDITOR
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.AUDIT_OPERATION, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        assert not module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)

    def test_synthesizer_permissions(self):
        """Property: Synthesizer_Consolidator has correct permissions.
        
        Synthesizer_Consolidator can: collect_artifacts, query_artifact, attach_metadata, propagate_trace
        """
        module = RoleTraceValidationModule()
        role = CanonicalRole.SYNTHESIZER_CONSOLIDATOR
        trace_id = "run_001:branch_001:leaf_001"
        
        # Allowed operations
        assert module.validate_operation_for_role(role, OperationCategory.COLLECT_ARTIFACTS, trace_id)
        
        # Disallowed operations
        assert not module.validate_operation_for_role(role, OperationCategory.EXECUTE_TASK, trace_id)
        assert not module.validate_operation_for_role(role, OperationCategory.VERIFY_RESULT, trace_id)


class TestTraceMetadataProperties:
    """Property-based tests for trace metadata attachment.
    
    **Validates: Requirements 3.4**
    """

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50)
    )
    def test_attached_metadata_is_retrievable(self, trace_id, canonical_group, role_name):
        """Property: Attached metadata can be retrieved from artifact.
        
        After attaching metadata to an artifact, it must be retrievable.
        """
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        
        result = module.attach_trace_metadata(
            artifact,
            trace_id,
            canonical_group,
            role_name
        )
        
        metadata = module.extract_trace_metadata(result)
        assert metadata is not None
        assert metadata.trace_id == trace_id
        assert metadata.canonical_group == canonical_group
        assert metadata.role_name == role_name

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50)
    )
    def test_attached_metadata_includes_timestamp(self, trace_id, canonical_group, role_name):
        """Property: Attached metadata includes a valid timestamp.
        
        The timestamp must be a positive number representing seconds since epoch.
        """
        module = RoleTraceValidationModule()
        before = datetime.now().timestamp()
        
        result = module.attach_trace_metadata(
            {},
            trace_id,
            canonical_group,
            role_name
        )
        
        after = datetime.now().timestamp()
        timestamp = result["_trace_metadata"]["timestamp"]
        
        assert isinstance(timestamp, float)
        assert before <= timestamp <= after

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50),
        operation_name=st.text(min_size=1, max_size=50)
    )
    def test_attached_metadata_preserves_operation_name(self, trace_id, canonical_group, role_name, operation_name):
        """Property: Attached metadata preserves operation_name.
        
        If operation_name is provided, it must be stored in metadata.
        """
        module = RoleTraceValidationModule()
        
        result = module.attach_trace_metadata(
            {},
            trace_id,
            canonical_group,
            role_name,
            operation_name=operation_name
        )
        
        assert result["_trace_metadata"]["operation_name"] == operation_name

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50),
        metadata_dict=st.dictionaries(st.text(min_size=1), st.text(min_size=1), max_size=5)
    )
    def test_attached_metadata_preserves_additional_metadata(self, trace_id, canonical_group, role_name, metadata_dict):
        """Property: Attached metadata preserves additional metadata.
        
        If additional metadata is provided, it must be stored in the metadata field.
        """
        module = RoleTraceValidationModule()
        
        result = module.attach_trace_metadata(
            {},
            trace_id,
            canonical_group,
            role_name,
            metadata=metadata_dict
        )
        
        assert result["_trace_metadata"]["metadata"] == metadata_dict

    @given(
        artifact_dict=st.dictionaries(st.text(min_size=1), st.text(min_size=1), max_size=5),
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50)
    )
    def test_attached_metadata_preserves_artifact_content(self, artifact_dict, trace_id, canonical_group, role_name):
        """Property: Attached metadata preserves original artifact content.
        
        All original artifact fields must be preserved after attaching metadata.
        """
        module = RoleTraceValidationModule()
        
        result = module.attach_trace_metadata(
            artifact_dict,
            trace_id,
            canonical_group,
            role_name
        )
        
        # All original fields should be present
        for key, value in artifact_dict.items():
            assert result[key] == value

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50)
    )
    def test_metadata_attachment_is_logged(self, trace_id, canonical_group, role_name):
        """Property: Metadata attachment is logged.
        
        Each metadata attachment must be recorded in the trace_metadata_log.
        """
        module = RoleTraceValidationModule()
        initial_count = len(module.trace_metadata_log)
        
        module.attach_trace_metadata(
            {},
            trace_id,
            canonical_group,
            role_name
        )
        
        assert len(module.trace_metadata_log) == initial_count + 1
        assert module.trace_metadata_log[-1].trace_id == trace_id

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        canonical_group=st.text(min_size=1, max_size=50),
        role_name=st.text(min_size=1, max_size=50)
    )
    def test_metadata_consistency_validation(self, trace_id, canonical_group, role_name):
        """Property: Metadata consistency can be validated.
        
        After attaching metadata with a trace_id, validation should pass for the same trace_id.
        """
        module = RoleTraceValidationModule()
        artifact = module.attach_trace_metadata(
            {},
            trace_id,
            canonical_group,
            role_name
        )
        
        result = module.validate_trace_metadata_consistency(artifact, trace_id)
        assert result is True


class TestTracePropagationProperties:
    """Property-based tests for trace_id propagation.
    
    **Validates: Requirements 3.5**
    """

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_preserves_trace_id(self, trace_id, role):
        """Property: Trace_id propagation preserves the trace_id.
        
        After propagating a trace_id, the artifact must contain the same trace_id.
        """
        module = RoleTraceValidationModule()
        artifact = {}
        
        result = module.propagate_trace_id(trace_id, artifact, role)
        
        assert result["_trace_metadata"]["trace_id"] == trace_id

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        artifact_dict=st.dictionaries(st.text(min_size=1), st.text(min_size=1), max_size=5),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_preserves_artifact_content(self, trace_id, artifact_dict, role):
        """Property: Trace_id propagation preserves artifact content.
        
        All original artifact fields must be preserved after propagating trace_id.
        """
        module = RoleTraceValidationModule()
        
        result = module.propagate_trace_id(trace_id, artifact_dict, role)
        
        # All original fields should be present
        for key, value in artifact_dict.items():
            assert result[key] == value

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_allowed_for_all_roles(self, trace_id, role):
        """Property: Trace_id propagation is allowed for all roles.
        
        All roles must be able to propagate trace_id without raising an exception.
        """
        module = RoleTraceValidationModule()
        
        # Should not raise an exception
        result = module.propagate_trace_id(trace_id, {}, role)
        assert result["_trace_metadata"]["trace_id"] == trace_id

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_overwrites_existing_trace_id(self, trace_id, role):
        """Property: Trace_id propagation overwrites existing trace_id.
        
        If an artifact already has a trace_id, propagating a new one should overwrite it.
        """
        module = RoleTraceValidationModule()
        old_trace_id = "run_001:branch_001:leaf_001"
        artifact = {
            "_trace_metadata": {
                "trace_id": old_trace_id
            }
        }
        
        result = module.propagate_trace_id(trace_id, artifact, role)
        
        assert result["_trace_metadata"]["trace_id"] == trace_id
        assert result["_trace_metadata"]["trace_id"] != old_trace_id

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_creates_metadata_if_missing(self, trace_id, role):
        """Property: Trace_id propagation creates metadata if missing.
        
        If an artifact doesn't have _trace_metadata, propagation should create it.
        """
        module = RoleTraceValidationModule()
        artifact = {"content": "test"}
        
        result = module.propagate_trace_id(trace_id, artifact, role)
        
        assert "_trace_metadata" in result
        assert result["_trace_metadata"]["trace_id"] == trace_id

    @given(
        trace_id=st.text(min_size=1, max_size=100),
        role=st.sampled_from(list(CanonicalRole))
    )
    def test_trace_id_propagation_is_idempotent(self, trace_id, role):
        """Property: Trace_id propagation is idempotent.
        
        Propagating the same trace_id multiple times should produce the same result.
        """
        module = RoleTraceValidationModule()
        artifact = {}
        
        result1 = module.propagate_trace_id(trace_id, artifact, role)
        result2 = module.propagate_trace_id(trace_id, result1, role)
        
        assert result1["_trace_metadata"]["trace_id"] == result2["_trace_metadata"]["trace_id"]
