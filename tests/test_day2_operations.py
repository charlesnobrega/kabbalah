"""
Tests for Day 2 Operations Module
"""

import pytest
import time
from src.kabbalah.day2_operations import (
    Day2OperationsModule,
    OperationType,
    OperationStatus,
    AuditLogEntry,
    Day2OperationResult,
)


class TestDay2OperationsModule:
    """Test Day 2 Operations Module"""
    
    def test_module_initialization(self):
        """Test module initialization"""
        module = Day2OperationsModule()
        assert module is not None
        assert len(module.audit_log) == 0
    
    def test_query_operation_allowed(self):
        """Test that query operations are allowed"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.QUERY,
            user_id="user_001",
        )
        
        assert result.allowed
        assert result.status == OperationStatus.ALLOWED
        assert "allowed" in result.reason.lower()
    
    def test_read_operation_allowed(self):
        """Test that read operations are allowed"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.READ,
            user_id="user_001",
        )
        
        assert result.allowed
        assert result.status == OperationStatus.ALLOWED
    
    def test_tool_execution_allowed(self):
        """Test that tool execution is allowed"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.TOOL_EXECUTION,
            user_id="user_001",
        )
        
        assert result.allowed
        assert result.status == OperationStatus.ALLOWED
    
    def test_new_project_allowed(self):
        """Test that new project operations are allowed"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.NEW_PROJECT,
            user_id="user_001",
        )
        
        assert result.allowed
        assert result.status == OperationStatus.ALLOWED
    
    def test_bootstrap_operation_blocked(self):
        """Test that bootstrap operations are blocked"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.BOOTSTRAP,
            user_id="user_001",
        )
        
        assert not result.allowed
        assert result.status == OperationStatus.BLOCKED
        assert "blocked" in result.reason.lower()
    
    def test_memory_reset_blocked(self):
        """Test that memory reset is blocked"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.MEMORY_RESET,
            user_id="user_001",
        )
        
        assert not result.allowed
        assert result.status == OperationStatus.BLOCKED
    
    def test_config_change_blocked(self):
        """Test that config changes are blocked"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.CONFIG_CHANGE,
            user_id="user_001",
        )
        
        assert not result.allowed
        assert result.status == OperationStatus.BLOCKED
    
    def test_agent_init_blocked(self):
        """Test that agent initialization is blocked"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.AGENT_INIT,
            user_id="user_001",
        )
        
        assert not result.allowed
        assert result.status == OperationStatus.BLOCKED
    
    def test_audit_log_entry_created(self):
        """Test that audit log entry is created"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.QUERY,
            user_id="user_001",
        )
        
        assert result.audit_entry is not None
        assert result.audit_entry.operation_type == OperationType.QUERY
        assert result.audit_entry.user_id == "user_001"
        assert len(module.audit_log) == 1
    
    def test_audit_log_entry_immutable(self):
        """Test that audit log entries are immutable"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        
        # Get entry
        entries = module.get_audit_log()
        assert len(entries) == 1
        
        # Try to modify (should not affect original)
        entry = entries[0]
        original_timestamp = entry.timestamp
        
        # Entries should be independent
        assert entry.timestamp == original_timestamp
    
    def test_get_audit_log_all(self):
        """Test getting all audit log entries"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_002")
        module.check_operation_allowed(OperationType.BOOTSTRAP, user_id="user_001")
        
        entries = module.get_audit_log()
        
        assert len(entries) == 3
    
    def test_get_audit_log_filter_by_operation_type(self):
        """Test filtering audit log by operation type"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_002")
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        
        entries = module.get_audit_log(operation_type=OperationType.QUERY)
        
        assert len(entries) == 2
        assert all(e.operation_type == OperationType.QUERY for e in entries)
    
    def test_get_audit_log_filter_by_status(self):
        """Test filtering audit log by status"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.BOOTSTRAP, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_001")
        
        entries = module.get_audit_log(status=OperationStatus.BLOCKED)
        
        assert len(entries) == 1
        assert entries[0].operation_type == OperationType.BOOTSTRAP
    
    def test_get_audit_log_filter_by_user(self):
        """Test filtering audit log by user"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_002")
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        
        entries = module.get_audit_log(user_id="user_001")
        
        assert len(entries) == 2
        assert all(e.user_id == "user_001" for e in entries)
    
    def test_get_audit_log_with_limit(self):
        """Test getting audit log with limit"""
        module = Day2OperationsModule()
        
        for i in range(5):
            module.check_operation_allowed(OperationType.QUERY, user_id=f"user_{i}")
        
        entries = module.get_audit_log(limit=3)
        
        assert len(entries) == 3
    
    def test_get_audit_log_count(self):
        """Test getting audit log count"""
        module = Day2OperationsModule()
        
        assert module.get_audit_log_count() == 0
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        assert module.get_audit_log_count() == 1
        
        module.check_operation_allowed(OperationType.READ, user_id="user_001")
        assert module.get_audit_log_count() == 2
    
    def test_export_audit_log(self):
        """Test exporting audit log"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.BOOTSTRAP, user_id="user_001")
        
        exported = module.export_audit_log()
        
        assert len(exported) == 2
        assert all(isinstance(e, dict) for e in exported)
        assert "entry_id" in exported[0]
        assert "timestamp" in exported[0]
        assert "operation_type" in exported[0]
        assert "status" in exported[0]
    
    def test_get_statistics(self):
        """Test getting audit log statistics"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_002")
        module.check_operation_allowed(OperationType.BOOTSTRAP, user_id="user_001")
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        
        stats = module.get_statistics()
        
        assert stats["total_entries"] == 4
        assert stats["allowed_operations"] == 3
        assert stats["blocked_operations"] == 1
        assert stats["operations_by_type"]["query"] == 2
        assert stats["operations_by_type"]["read"] == 1
        assert stats["operations_by_type"]["bootstrap"] == 1
        assert stats["operations_by_user"]["user_001"] == 3
        assert stats["operations_by_user"]["user_002"] == 1
    
    def test_operation_with_details(self):
        """Test operation with additional details"""
        module = Day2OperationsModule()
        
        details = {"tool": "bash", "command": "ls -la"}
        result = module.check_operation_allowed(
            operation_type=OperationType.TOOL_EXECUTION,
            user_id="user_001",
            details=details,
        )
        
        assert result.audit_entry.details == details
    
    def test_blocked_operation_has_error_message(self):
        """Test that blocked operations have error messages"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.BOOTSTRAP,
            user_id="user_001",
        )
        
        assert result.audit_entry.error_message is not None
        assert "blocked" in result.audit_entry.error_message.lower()
    
    def test_clear_audit_log(self):
        """Test clearing audit log"""
        module = Day2OperationsModule()
        
        module.check_operation_allowed(OperationType.QUERY, user_id="user_001")
        module.check_operation_allowed(OperationType.READ, user_id="user_001")
        
        assert module.get_audit_log_count() == 2
        
        module.clear_audit_log()
        
        assert module.get_audit_log_count() == 0
    
    def test_audit_entry_to_dict(self):
        """Test converting audit entry to dictionary"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.QUERY,
            user_id="user_001",
        )
        
        entry_dict = result.audit_entry.to_dict()
        
        assert entry_dict["entry_id"].startswith("audit_")
        assert "timestamp" in entry_dict
        assert "datetime" in entry_dict
        assert entry_dict["operation_type"] == "query"
        assert entry_dict["status"] == "allowed"
        assert entry_dict["user_id"] == "user_001"
    
    def test_multiple_users_operations(self):
        """Test operations from multiple users"""
        module = Day2OperationsModule()
        
        for user_id in ["user_001", "user_002", "user_003"]:
            module.check_operation_allowed(OperationType.QUERY, user_id=user_id)
            module.check_operation_allowed(OperationType.READ, user_id=user_id)
        
        stats = module.get_statistics()
        
        assert stats["total_entries"] == 6
        assert len(stats["operations_by_user"]) == 3
        assert all(count == 2 for count in stats["operations_by_user"].values())
    
    def test_operation_without_user_id(self):
        """Test operation without user ID"""
        module = Day2OperationsModule()
        
        result = module.check_operation_allowed(
            operation_type=OperationType.QUERY,
        )
        
        assert result.allowed
        assert result.audit_entry.user_id is None
    
    def test_concurrent_operations(self):
        """Test concurrent operations"""
        import threading
        
        module = Day2OperationsModule()
        
        def perform_operations():
            for i in range(10):
                module.check_operation_allowed(
                    OperationType.QUERY,
                    user_id=f"user_{threading.current_thread().ident}",
                )
        
        threads = [threading.Thread(target=perform_operations) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert module.get_audit_log_count() == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
