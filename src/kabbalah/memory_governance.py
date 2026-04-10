"""Memory Governance Module for Kabbalah - Access control and audit logging."""

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryCategory(Enum):
    """Memory categories for access control."""
    SHARED = "shared"  # Accessible to all agents
    DOMAIN_SPECIFIC = "domain-specific"  # Accessible to agents in domain
    ROLE_SPECIFIC = "role-specific"  # Accessible to agents with role


class MemoryOperation(Enum):
    """Memory operations for access control."""
    READ = "read"
    WRITE = "write"


# Canonical roles from the system
CANONICAL_ROLES = {
    "Intake_Clarifier",
    "Root_Planner",
    "Domain_Coordinator",
    "Leaf_Builder",
    "Leaf_Verifier",
    "Leaf_Auditor",
    "Synthesizer_Consolidator",
}


@dataclass
class AccessControlPolicy:
    """Access control policy for memory operations."""
    memory_category: str
    operation: str
    allowed_roles: Set[str] = field(default_factory=set)
    allowed_domains: Set[str] = field(default_factory=set)


@dataclass
class MemoryAccessLog:
    """Log entry for memory access."""
    access_id: str
    agent_role: str
    memory_category: str
    operation: str
    trace_id: str
    allowed: bool
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryGovernanceModule:
    """
    Memory Governance Module for Kabbalah.

    Enforces access control on memory operations and maintains audit logs.
    Supports role-based access control with memory categories:
    - shared: Accessible to all agents
    - domain-specific: Accessible to agents in domain
    - role-specific: Accessible to agents with role
    """

    def __init__(self, audit_log_path: Optional[str] = None):
        """
        Initialize MemoryGovernanceModule.

        Args:
            audit_log_path: Optional path for audit log storage
        """
        self.audit_log_path = Path(
            audit_log_path or os.path.join(
                os.path.expanduser("~"), ".kabbalah", "audit"
            )
        )
        self.audit_log_path.mkdir(parents=True, exist_ok=True)
        self.audit_log_file = self.audit_log_path / "memory_access.jsonl"
        self.lock = threading.RLock()
        self.access_counter = 0

        # Initialize default access control policies
        self.policies = self._initialize_default_policies()

        logger.info(f"MemoryGovernanceModule initialized with audit log at {self.audit_log_path}")

    def _initialize_default_policies(self) -> Dict[str, AccessControlPolicy]:
        """Initialize default access control policies."""
        policies = {}

        # Shared memory: all roles can read and write
        policies["shared_read"] = AccessControlPolicy(
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.READ.value,
            allowed_roles=CANONICAL_ROLES.copy(),
        )
        policies["shared_write"] = AccessControlPolicy(
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.WRITE.value,
            allowed_roles=CANONICAL_ROLES.copy(),
        )

        # Domain-specific memory: domain coordinators and leaf nodes can access
        domain_roles = {
            "Domain_Coordinator",
            "Leaf_Builder",
            "Leaf_Verifier",
            "Leaf_Auditor",
        }
        policies["domain_specific_read"] = AccessControlPolicy(
            memory_category=MemoryCategory.DOMAIN_SPECIFIC.value,
            operation=MemoryOperation.READ.value,
            allowed_roles=domain_roles.copy(),
        )
        policies["domain_specific_write"] = AccessControlPolicy(
            memory_category=MemoryCategory.DOMAIN_SPECIFIC.value,
            operation=MemoryOperation.WRITE.value,
            allowed_roles=domain_roles.copy(),
        )

        # Role-specific memory: only agents with matching role can access
        # This is handled dynamically in check_memory_access
        policies["role_specific_read"] = AccessControlPolicy(
            memory_category=MemoryCategory.ROLE_SPECIFIC.value,
            operation=MemoryOperation.READ.value,
            allowed_roles=set(),  # Checked dynamically
        )
        policies["role_specific_write"] = AccessControlPolicy(
            memory_category=MemoryCategory.ROLE_SPECIFIC.value,
            operation=MemoryOperation.WRITE.value,
            allowed_roles=set(),  # Checked dynamically
        )

        return policies

    def check_memory_access(
        self,
        agent_role: str,
        memory_category: str,
        operation: str,
    ) -> bool:
        """
        Check if agent can access memory.

        Args:
            agent_role: Agent's canonical role
            memory_category: Memory category (shared, domain-specific, role-specific)
            operation: Operation (read, write)

        Returns:
            True if access is allowed, False otherwise

        Raises:
            ValueError: If agent_role, memory_category, or operation is invalid
        """
        # Validate inputs
        if agent_role not in CANONICAL_ROLES:
            raise ValueError(f"Invalid agent role: {agent_role}")

        try:
            category = MemoryCategory(memory_category)
        except ValueError:
            raise ValueError(f"Invalid memory category: {memory_category}")

        try:
            op = MemoryOperation(operation)
        except ValueError:
            raise ValueError(f"Invalid operation: {operation}")

        # Check access based on category
        if category == MemoryCategory.SHARED:
            # All roles can access shared memory
            return True

        elif category == MemoryCategory.DOMAIN_SPECIFIC:
            # Domain coordinators and leaf nodes can access
            allowed_roles = {
                "Domain_Coordinator",
                "Leaf_Builder",
                "Leaf_Verifier",
                "Leaf_Auditor",
            }
            return agent_role in allowed_roles

        elif category == MemoryCategory.ROLE_SPECIFIC:
            # Only agents with matching role can access
            # Role-specific memory is keyed by role name
            # For now, all roles can access their own role-specific memory
            return True

        return False

    def log_memory_access(
        self,
        agent_role: str,
        memory_category: str,
        operation: str,
        trace_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log memory access for audit.

        Args:
            agent_role: Agent's canonical role
            memory_category: Memory category
            operation: Operation (read, write)
            trace_id: Trace identifier for audit
            metadata: Optional additional metadata

        Raises:
            ValueError: If agent_role, memory_category, or operation is invalid
        """
        # Validate inputs
        if agent_role not in CANONICAL_ROLES:
            raise ValueError(f"Invalid agent role: {agent_role}")

        try:
            category = MemoryCategory(memory_category)
        except ValueError:
            raise ValueError(f"Invalid memory category: {memory_category}")

        try:
            op = MemoryOperation(operation)
        except ValueError:
            raise ValueError(f"Invalid operation: {operation}")

        try:
            with self.lock:
                # Check if access is allowed
                allowed = self.check_memory_access(agent_role, memory_category, operation)

                # Create log entry
                self.access_counter += 1
                log_entry = MemoryAccessLog(
                    access_id=f"access_{self.access_counter:06d}",
                    agent_role=agent_role,
                    memory_category=memory_category,
                    operation=operation,
                    trace_id=trace_id,
                    allowed=allowed,
                    metadata=metadata or {},
                )

                # Write to audit log
                self._write_audit_log(log_entry)

                # Log appropriately
                if allowed:
                    logger.info(
                        f"Memory access allowed: {agent_role} {operation} {memory_category} "
                        f"(trace_id: {trace_id})"
                    )
                else:
                    logger.warning(
                        f"Memory access denied: {agent_role} {operation} {memory_category} "
                        f"(trace_id: {trace_id})"
                    )

        except Exception as e:
            logger.error(f"Error logging memory access: {e}", exc_info=True)
            raise RuntimeError(f"Critical audit logging failure. Access enforcement blocked: {e}") from e

    def _write_audit_log(self, log_entry: MemoryAccessLog) -> None:
        """Write audit log entry to file."""
        try:
            with open(self.audit_log_file, "a") as f:
                f.write(json.dumps(asdict(log_entry)) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            raise RuntimeError(f"Audit log write failed on disk: {e}") from e

    def get_access_logs(
        self,
        agent_role: Optional[str] = None,
        memory_category: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryAccessLog]:
        """
        Get access logs with optional filtering.

        Args:
            agent_role: Optional filter by agent role
            memory_category: Optional filter by memory category
            trace_id: Optional filter by trace_id
            limit: Maximum number of logs to return

        Returns:
            List of matching access logs
        """
        try:
            with self.lock:
                logs = []

                if not self.audit_log_file.exists():
                    return logs

                with open(self.audit_log_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            log_entry = MemoryAccessLog(**data)

                            # Apply filters
                            if agent_role and log_entry.agent_role != agent_role:
                                continue
                            if memory_category and log_entry.memory_category != memory_category:
                                continue
                            if trace_id and log_entry.trace_id != trace_id:
                                continue

                            logs.append(log_entry)

                # Return most recent logs up to limit
                return logs[-limit:]

        except Exception as e:
            logger.error(f"Error reading access logs: {e}")
            return []

    def clear_audit_logs(self) -> bool:
        """
        Clear all audit logs (for testing/reset).

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                if self.audit_log_file.exists():
                    self.audit_log_file.unlink()
                    self.access_counter = 0
                    logger.info("Cleared audit logs")
                return True
        except Exception as e:
            logger.error(f"Error clearing audit logs: {e}")
            return False

    def add_policy(self, policy_key: str, policy: AccessControlPolicy) -> None:
        """
        Add or update an access control policy.

        Args:
            policy_key: Unique key for the policy
            policy: Access control policy
        """
        with self.lock:
            self.policies[policy_key] = policy
            logger.info(f"Added/updated policy: {policy_key}")

    def get_policies(self) -> Dict[str, AccessControlPolicy]:
        """
        Get all access control policies.

        Returns:
            Dictionary of policies
        """
        with self.lock:
            return dict(self.policies)
