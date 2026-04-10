"""Role Trace Validation Module for runtime hardening.

This module validates that each agent operates within its assigned role,
attaches trace metadata to artifacts, and propagates trace_id through operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum


class CanonicalRole(Enum):
    """Canonical roles in the Kabbalah system."""
    INTAKE_CLARIFIER = "Intake_Clarifier"
    ROOT_PLANNER = "Root_Planner"
    DOMAIN_COORDINATOR = "Domain_Coordinator"
    LEAF_BUILDER = "Leaf_Builder"
    LEAF_VERIFIER = "Leaf_Verifier"
    LEAF_AUDITOR = "Leaf_Auditor"
    SYNTHESIZER_CONSOLIDATOR = "Synthesizer_Consolidator"


class OperationCategory(Enum):
    """Categories of operations that can be performed."""
    PARSE_REQUEST = "parse_request"
    DECOMPOSE_SPECIFICATION = "decompose_specification"
    SPAWN_LEAF_NODES = "spawn_leaf_nodes"
    EXECUTE_TASK = "execute_task"
    VERIFY_RESULT = "verify_result"
    AUDIT_OPERATION = "audit_operation"
    COLLECT_ARTIFACTS = "collect_artifacts"
    ATTACH_METADATA = "attach_metadata"
    PROPAGATE_TRACE = "propagate_trace"
    QUERY_ARTIFACT = "query_artifact"


@dataclass
class TraceMetadata:
    """Trace metadata attached to artifacts."""
    trace_id: str  # Format: run_id:branch_id:leaf_id
    canonical_group: str  # The canonical role group
    role_name: str  # The specific role name
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    operation_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleViolation:
    """Record of a role-based operation violation."""
    role: CanonicalRole
    operation: OperationCategory
    trace_id: str
    timestamp: float
    violation_type: str
    message: str


class RoleTraceValidationModule:
    """Validates role-based operations and manages trace metadata.
    
    This module ensures that:
    - Each agent operates within its assigned role
    - Operations are validated against role permissions
    - Trace metadata is attached to all artifacts
    - Trace_id is propagated through all operations
    - Complete auditability is maintained
    """

    # Define which operations are allowed for each role
    ROLE_PERMISSIONS: Dict[CanonicalRole, Set[OperationCategory]] = {
        CanonicalRole.INTAKE_CLARIFIER: {
            OperationCategory.PARSE_REQUEST,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
        },
        CanonicalRole.ROOT_PLANNER: {
            OperationCategory.DECOMPOSE_SPECIFICATION,
            OperationCategory.SPAWN_LEAF_NODES,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
        },
        CanonicalRole.DOMAIN_COORDINATOR: {
            OperationCategory.SPAWN_LEAF_NODES,
            OperationCategory.EXECUTE_TASK,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
        },
        CanonicalRole.LEAF_BUILDER: {
            OperationCategory.EXECUTE_TASK,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
            OperationCategory.QUERY_ARTIFACT,
        },
        CanonicalRole.LEAF_VERIFIER: {
            OperationCategory.VERIFY_RESULT,
            OperationCategory.EXECUTE_TASK,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
        },
        CanonicalRole.LEAF_AUDITOR: {
            OperationCategory.AUDIT_OPERATION,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
        },
        CanonicalRole.SYNTHESIZER_CONSOLIDATOR: {
            OperationCategory.COLLECT_ARTIFACTS,
            OperationCategory.QUERY_ARTIFACT,
            OperationCategory.ATTACH_METADATA,
            OperationCategory.PROPAGATE_TRACE,
        },
    }

    def __init__(self):
        """Initialize the RoleTraceValidationModule."""
        self._violation_log: List[RoleViolation] = []
        self._trace_metadata_log: List[TraceMetadata] = []

    @property
    def violation_log(self) -> List[RoleViolation]:
        """Get immutable copy of violation log."""
        return list(self._violation_log)

    @property
    def trace_metadata_log(self) -> List[TraceMetadata]:
        """Get immutable copy of trace metadata log."""
        return list(self._trace_metadata_log)

    def validate_operation_for_role(
        self,
        role: CanonicalRole,
        operation: OperationCategory,
        trace_id: str
    ) -> bool:
        """Validate that an operation is permitted for a role.
        
        Args:
            role: The canonical role attempting the operation
            operation: The operation category being attempted
            trace_id: The trace_id for this operation
            
        Returns:
            True if operation is allowed, False otherwise
        """
        if role not in self.ROLE_PERMISSIONS:
            return False
        
        allowed_operations = self.ROLE_PERMISSIONS[role]
        is_allowed = operation in allowed_operations
        
        if not is_allowed:
            violation = RoleViolation(
                role=role,
                operation=operation,
                trace_id=trace_id,
                timestamp=datetime.now().timestamp(),
                violation_type="UNAUTHORIZED_OPERATION_FOR_ROLE",
                message=f"Role {role.value} is not permitted to perform {operation.value}"
            )
            self._violation_log.append(violation)
        
        return is_allowed

    def validate_operation_for_role_with_logging(
        self,
        role: CanonicalRole,
        operation: OperationCategory,
        trace_id: str
    ) -> tuple[bool, Optional[str]]:
        """Validate operation and return result with error message.
        
        Args:
            role: The canonical role attempting the operation
            operation: The operation category being attempted
            trace_id: The trace_id for this operation
            
        Returns:
            Tuple of (is_allowed, error_message)
            If allowed, error_message is None
            If not allowed, error_message contains violation details
        """
        is_allowed = self.validate_operation_for_role(role, operation, trace_id)
        
        if not is_allowed:
            error_msg = (
                f"Operation {operation.value} is not allowed for role {role.value}. "
                f"Trace ID: {trace_id}"
            )
            return False, error_msg
        
        return True, None

    def attach_trace_metadata(
        self,
        artifact: Dict[str, Any],
        trace_id: str,
        canonical_group: str,
        role_name: str,
        operation_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attach trace metadata to an artifact.
        
        Args:
            artifact: The artifact to attach metadata to
            trace_id: The hierarchical trace identifier (run_id:branch_id:leaf_id)
            canonical_group: The canonical role group
            role_name: The specific role name
            operation_name: Optional name of the operation that created the artifact
            metadata: Optional additional metadata
            
        Returns:
            The artifact with attached trace metadata
        """
        trace_metadata = TraceMetadata(
            trace_id=trace_id,
            canonical_group=canonical_group,
            role_name=role_name,
            operation_name=operation_name,
            metadata=metadata or {}
        )
        
        # Attach metadata to artifact
        artifact_with_metadata = dict(artifact)
        artifact_with_metadata["_trace_metadata"] = {
            "trace_id": trace_metadata.trace_id,
            "canonical_group": trace_metadata.canonical_group,
            "role_name": trace_metadata.role_name,
            "timestamp": trace_metadata.timestamp,
            "operation_name": trace_metadata.operation_name,
            "metadata": trace_metadata.metadata,
        }
        
        # Log the metadata attachment
        self._trace_metadata_log.append(trace_metadata)
        
        return artifact_with_metadata

    def propagate_trace_id(
        self,
        source_trace_id: str,
        target_artifact: Dict[str, Any],
        role: CanonicalRole
    ) -> Dict[str, Any]:
        """Propagate trace_id through operations.
        
        Args:
            source_trace_id: The trace_id to propagate
            target_artifact: The artifact to propagate trace_id to
            role: The role performing the propagation
            
        Returns:
            The artifact with propagated trace_id
        """
        # Validate that propagation is allowed for this role
        is_allowed = self.validate_operation_for_role(
            role,
            OperationCategory.PROPAGATE_TRACE,
            source_trace_id
        )
        
        if not is_allowed:
            raise ValueError(
                f"Role {role.value} is not permitted to propagate trace_id"
            )
        
        # Propagate the trace_id
        artifact_with_trace = dict(target_artifact)
        if "_trace_metadata" not in artifact_with_trace:
            artifact_with_trace["_trace_metadata"] = {}
        
        artifact_with_trace["_trace_metadata"]["trace_id"] = source_trace_id
        
        return artifact_with_trace

    def get_violation_history(self) -> List[RoleViolation]:
        """Get complete violation history."""
        return list(self._violation_log)

    def get_violations_for_role(self, role: CanonicalRole) -> List[RoleViolation]:
        """Get violations for a specific role."""
        return [v for v in self._violation_log if v.role == role]

    def get_violations_for_operation(
        self,
        operation: OperationCategory
    ) -> List[RoleViolation]:
        """Get violations for a specific operation."""
        return [v for v in self._violation_log if v.operation == operation]

    def get_violations_by_trace_id(self, trace_id: str) -> List[RoleViolation]:
        """Get violations for a specific trace_id."""
        return [v for v in self._violation_log if v.trace_id == trace_id]

    def get_trace_metadata_for_trace_id(self, trace_id: str) -> List[TraceMetadata]:
        """Get all trace metadata for a specific trace_id."""
        return [m for m in self._trace_metadata_log if m.trace_id == trace_id]

    def get_trace_metadata_for_role(self, role_name: str) -> List[TraceMetadata]:
        """Get all trace metadata for a specific role."""
        return [m for m in self._trace_metadata_log if m.role_name == role_name]

    def extract_trace_metadata(self, artifact: Dict[str, Any]) -> Optional[TraceMetadata]:
        """Extract trace metadata from an artifact.
        
        Args:
            artifact: The artifact to extract metadata from
            
        Returns:
            TraceMetadata if present, None otherwise
        """
        if "_trace_metadata" not in artifact:
            return None
        
        metadata_dict = artifact["_trace_metadata"]
        return TraceMetadata(
            trace_id=metadata_dict.get("trace_id", ""),
            canonical_group=metadata_dict.get("canonical_group", ""),
            role_name=metadata_dict.get("role_name", ""),
            timestamp=metadata_dict.get("timestamp", datetime.now().timestamp()),
            operation_name=metadata_dict.get("operation_name"),
            metadata=metadata_dict.get("metadata", {})
        )

    def validate_trace_metadata_consistency(
        self,
        artifact: Dict[str, Any],
        expected_trace_id: str
    ) -> bool:
        """Validate that artifact's trace metadata is consistent.
        
        Args:
            artifact: The artifact to validate
            expected_trace_id: The expected trace_id
            
        Returns:
            True if metadata is consistent, False otherwise
        """
        metadata = self.extract_trace_metadata(artifact)
        if metadata is None:
            return False
        
        return metadata.trace_id == expected_trace_id
