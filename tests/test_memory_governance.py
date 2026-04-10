"""Unit tests for MemoryGovernanceModule."""

import json
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from kabbalah.memory_governance import (
    MemoryGovernanceModule,
    MemoryCategory,
    MemoryOperation,
    AccessControlPolicy,
    MemoryAccessLog,
    CANONICAL_ROLES,
)


class TestMemoryGovernanceModuleInitialization:
    """Test MemoryGovernanceModule initialization."""

    def test_initialization_with_default_path(self):
        """Test initialization with default audit log path."""
        module = MemoryGovernanceModule()
        assert module.audit_log_path is not None
        assert module.audit_log_file is not None
        assert module.lock is not None
        assert module.access_counter == 0
        assert len(module.policies) > 0

    def test_initialization_with_custom_path(self):
        """Test initialization with custom audit log path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            assert str(module.audit_log_path) == tmpdir
            assert module.audit_log_file == Path(tmpdir) / "memory_access.jsonl"

    def test_default_policies_created(self):
        """Test that default policies are created."""
        module = MemoryGovernanceModule()
        policies = module.get_policies()

        # Should have policies for shared, domain-specific, and role-specific
        assert "shared_read" in policies
        assert "shared_write" in policies
        assert "domain_specific_read" in policies
        assert "domain_specific_write" in policies
        assert "role_specific_read" in policies
        assert "role_specific_write" in policies

    def test_shared_policy_includes_all_roles(self):
        """Test that shared memory policy includes all canonical roles."""
        module = MemoryGovernanceModule()
        policies = module.get_policies()

        shared_read = policies["shared_read"]
        assert shared_read.allowed_roles == CANONICAL_ROLES


class TestCheckMemoryAccess:
    """Test check_memory_access method."""

    def test_shared_memory_accessible_to_all_roles(self):
        """Test that shared memory is accessible to all roles."""
        module = MemoryGovernanceModule()

        for role in CANONICAL_ROLES:
            assert module.check_memory_access(
                role, MemoryCategory.SHARED.value, MemoryOperation.READ.value
            )
            assert module.check_memory_access(
                role, MemoryCategory.SHARED.value, MemoryOperation.WRITE.value
            )

    def test_domain_specific_memory_accessible_to_domain_roles(self):
        """Test that domain-specific memory is accessible to domain roles."""
        module = MemoryGovernanceModule()

        domain_roles = {
            "Domain_Coordinator",
            "Leaf_Builder",
            "Leaf_Verifier",
            "Leaf_Auditor",
        }

        for role in domain_roles:
            assert module.check_memory_access(
                role, MemoryCategory.DOMAIN_SPECIFIC.value, MemoryOperation.READ.value
            )
            assert module.check_memory_access(
                role, MemoryCategory.DOMAIN_SPECIFIC.value, MemoryOperation.WRITE.value
            )

    def test_domain_specific_memory_denied_to_non_domain_roles(self):
        """Test that domain-specific memory is denied to non-domain roles."""
        module = MemoryGovernanceModule()

        non_domain_roles = {"Intake_Clarifier", "Root_Planner", "Synthesizer_Consolidator"}

        for role in non_domain_roles:
            assert not module.check_memory_access(
                role, MemoryCategory.DOMAIN_SPECIFIC.value, MemoryOperation.READ.value
            )
            assert not module.check_memory_access(
                role, MemoryCategory.DOMAIN_SPECIFIC.value, MemoryOperation.WRITE.value
            )

    def test_role_specific_memory_accessible_to_all_roles(self):
        """Test that role-specific memory is accessible to all roles."""
        module = MemoryGovernanceModule()

        for role in CANONICAL_ROLES:
            assert module.check_memory_access(
                role, MemoryCategory.ROLE_SPECIFIC.value, MemoryOperation.READ.value
            )
            assert module.check_memory_access(
                role, MemoryCategory.ROLE_SPECIFIC.value, MemoryOperation.WRITE.value
            )

    def test_invalid_agent_role_raises_error(self):
        """Test that invalid agent role raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid agent role"):
            module.check_memory_access(
                "Invalid_Role", MemoryCategory.SHARED.value, MemoryOperation.READ.value
            )

    def test_invalid_memory_category_raises_error(self):
        """Test that invalid memory category raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid memory category"):
            module.check_memory_access(
                "Leaf_Builder", "invalid_category", MemoryOperation.READ.value
            )

    def test_invalid_operation_raises_error(self):
        """Test that invalid operation raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid operation"):
            module.check_memory_access(
                "Leaf_Builder", MemoryCategory.SHARED.value, "invalid_operation"
            )


class TestLogMemoryAccess:
    """Test log_memory_access method."""

    def test_log_allowed_access(self):
        """Test logging of allowed memory access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )

            # Verify log file was created
            assert module.audit_log_file.exists()

            # Read and verify log entry
            with open(module.audit_log_file, "r") as f:
                log_data = json.loads(f.readline())
                assert log_data["agent_role"] == "Leaf_Builder"
                assert log_data["memory_category"] == MemoryCategory.SHARED.value
                assert log_data["operation"] == MemoryOperation.READ.value
                assert log_data["trace_id"] == "run_001:branch_001:leaf_001"
                assert log_data["allowed"] is True

    def test_log_denied_access(self):
        """Test logging of denied memory access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            module.log_memory_access(
                "Intake_Clarifier",
                MemoryCategory.DOMAIN_SPECIFIC.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )

            # Verify log file was created
            assert module.audit_log_file.exists()

            # Read and verify log entry
            with open(module.audit_log_file, "r") as f:
                log_data = json.loads(f.readline())
                assert log_data["allowed"] is False

    def test_log_includes_metadata(self):
        """Test that log includes optional metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            metadata = {"resource_id": "res_123", "action": "query"}
            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
                metadata=metadata,
            )

            # Read and verify log entry
            with open(module.audit_log_file, "r") as f:
                log_data = json.loads(f.readline())
                assert log_data["metadata"] == metadata

    def test_log_invalid_agent_role_raises_error(self):
        """Test that logging with invalid agent role raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid agent role"):
            module.log_memory_access(
                "Invalid_Role",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )

    def test_log_invalid_memory_category_raises_error(self):
        """Test that logging with invalid memory category raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid memory category"):
            module.log_memory_access(
                "Leaf_Builder",
                "invalid_category",
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )

    def test_log_invalid_operation_raises_error(self):
        """Test that logging with invalid operation raises ValueError."""
        module = MemoryGovernanceModule()

        with pytest.raises(ValueError, match="Invalid operation"):
            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                "invalid_operation",
                "run_001:branch_001:leaf_001",
            )

    def test_log_increments_access_counter(self):
        """Test that logging increments access counter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            assert module.access_counter == 0

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )
            assert module.access_counter == 1

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.WRITE.value,
                "run_001:branch_001:leaf_001",
            )
            assert module.access_counter == 2


class TestGetAccessLogs:
    """Test get_access_logs method."""

    def test_get_all_logs(self):
        """Test retrieving all access logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            # Log multiple accesses
            for i in range(3):
                module.log_memory_access(
                    "Leaf_Builder",
                    MemoryCategory.SHARED.value,
                    MemoryOperation.READ.value,
                    f"run_001:branch_001:leaf_{i:03d}",
                )

            logs = module.get_access_logs()
            assert len(logs) == 3

    def test_filter_logs_by_agent_role(self):
        """Test filtering logs by agent role."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )
            module.log_memory_access(
                "Leaf_Verifier",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_002",
            )

            logs = module.get_access_logs(agent_role="Leaf_Builder")
            assert len(logs) == 1
            assert logs[0].agent_role == "Leaf_Builder"

    def test_filter_logs_by_memory_category(self):
        """Test filtering logs by memory category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )
            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.DOMAIN_SPECIFIC.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_002",
            )

            logs = module.get_access_logs(memory_category=MemoryCategory.SHARED.value)
            assert len(logs) == 1
            assert logs[0].memory_category == MemoryCategory.SHARED.value

    def test_filter_logs_by_trace_id(self):
        """Test filtering logs by trace_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )
            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_002",
            )

            logs = module.get_access_logs(trace_id="run_001:branch_001:leaf_001")
            assert len(logs) == 1
            assert logs[0].trace_id == "run_001:branch_001:leaf_001"

    def test_get_logs_respects_limit(self):
        """Test that get_access_logs respects limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            # Log 10 accesses
            for i in range(10):
                module.log_memory_access(
                    "Leaf_Builder",
                    MemoryCategory.SHARED.value,
                    MemoryOperation.READ.value,
                    f"run_001:branch_001:leaf_{i:03d}",
                )

            logs = module.get_access_logs(limit=5)
            assert len(logs) == 5

    def test_get_logs_returns_most_recent(self):
        """Test that get_access_logs returns most recent logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            # Log 5 accesses
            for i in range(5):
                module.log_memory_access(
                    "Leaf_Builder",
                    MemoryCategory.SHARED.value,
                    MemoryOperation.READ.value,
                    f"run_001:branch_001:leaf_{i:03d}",
                )

            logs = module.get_access_logs(limit=3)
            assert len(logs) == 3
            # Should be the last 3 logs
            assert logs[0].trace_id == "run_001:branch_001:leaf_002"
            assert logs[1].trace_id == "run_001:branch_001:leaf_003"
            assert logs[2].trace_id == "run_001:branch_001:leaf_004"


class TestClearAuditLogs:
    """Test clear_audit_logs method."""

    def test_clear_audit_logs(self):
        """Test clearing audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            # Log some accesses
            module.log_memory_access(
                "Leaf_Builder",
                MemoryCategory.SHARED.value,
                MemoryOperation.READ.value,
                "run_001:branch_001:leaf_001",
            )

            assert module.audit_log_file.exists()
            assert module.access_counter == 1

            # Clear logs
            result = module.clear_audit_logs()
            assert result is True
            assert not module.audit_log_file.exists()
            assert module.access_counter == 0

    def test_clear_audit_logs_when_empty(self):
        """Test clearing audit logs when no logs exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            result = module.clear_audit_logs()
            assert result is True


class TestAddPolicy:
    """Test add_policy method."""

    def test_add_new_policy(self):
        """Test adding a new access control policy."""
        module = MemoryGovernanceModule()

        policy = AccessControlPolicy(
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.READ.value,
            allowed_roles={"Leaf_Builder"},
        )

        module.add_policy("custom_policy", policy)

        policies = module.get_policies()
        assert "custom_policy" in policies
        assert policies["custom_policy"] == policy

    def test_update_existing_policy(self):
        """Test updating an existing policy."""
        module = MemoryGovernanceModule()

        new_policy = AccessControlPolicy(
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.READ.value,
            allowed_roles={"Leaf_Builder", "Leaf_Verifier"},
        )

        module.add_policy("shared_read", new_policy)

        policies = module.get_policies()
        assert policies["shared_read"] == new_policy


class TestThreadSafety:
    """Test thread safety of MemoryGovernanceModule."""

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)

            def log_access(thread_id):
                for i in range(10):
                    module.log_memory_access(
                        "Leaf_Builder",
                        MemoryCategory.SHARED.value,
                        MemoryOperation.READ.value,
                        f"run_001:branch_001:leaf_{thread_id}_{i:03d}",
                    )

            threads = [threading.Thread(target=log_access, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Should have 50 log entries (5 threads * 10 logs each)
            logs = module.get_access_logs(limit=100)
            assert len(logs) == 50
            assert module.access_counter == 50

    def test_concurrent_access_check(self):
        """Test concurrent access checks from multiple threads."""
        module = MemoryGovernanceModule()

        results = []

        def check_access(thread_id):
            for i in range(10):
                result = module.check_memory_access(
                    "Leaf_Builder",
                    MemoryCategory.SHARED.value,
                    MemoryOperation.READ.value,
                )
                results.append(result)

        threads = [threading.Thread(target=check_access, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All checks should succeed
        assert len(results) == 50
        assert all(results)


class TestMemoryAccessLog:
    """Test MemoryAccessLog dataclass."""

    def test_memory_access_log_creation(self):
        """Test creating a MemoryAccessLog."""
        log = MemoryAccessLog(
            access_id="access_000001",
            agent_role="Leaf_Builder",
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.READ.value,
            trace_id="run_001:branch_001:leaf_001",
            allowed=True,
        )

        assert log.access_id == "access_000001"
        assert log.agent_role == "Leaf_Builder"
        assert log.memory_category == MemoryCategory.SHARED.value
        assert log.operation == MemoryOperation.READ.value
        assert log.trace_id == "run_001:branch_001:leaf_001"
        assert log.allowed is True
        assert log.timestamp > 0
        assert log.metadata == {}

    def test_memory_access_log_with_metadata(self):
        """Test creating a MemoryAccessLog with metadata."""
        metadata = {"resource_id": "res_123"}
        log = MemoryAccessLog(
            access_id="access_000001",
            agent_role="Leaf_Builder",
            memory_category=MemoryCategory.SHARED.value,
            operation=MemoryOperation.READ.value,
            trace_id="run_001:branch_001:leaf_001",
            allowed=True,
            metadata=metadata,
        )

        assert log.metadata == metadata
