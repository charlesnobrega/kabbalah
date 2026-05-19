"""
Day 2 Operations Compliance Module

Enforces Day 2 operational constraints and immutable audit logging.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations in Day 2"""
    QUERY = "query"
    READ = "read"
    TOOL_EXECUTION = "tool_execution"
    NEW_PROJECT = "new_project"
    BOOTSTRAP = "bootstrap"
    MEMORY_RESET = "memory_reset"
    CONFIG_CHANGE = "config_change"
    AGENT_INIT = "agent_init"


class OperationStatus(Enum):
    """Status of an operation"""
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"


@dataclass
class AuditLogEntry:
    """Immutable audit log entry"""
    entry_id: str
    timestamp: float
    operation_type: OperationType
    status: OperationStatus
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "user_id": self.user_id,
            "details": self.details,
            "error_message": self.error_message,
        }


@dataclass
class Day2OperationResult:
    """Result of a Day 2 operation check"""
    allowed: bool
    operation_type: OperationType
    reason: str
    status: OperationStatus = OperationStatus.ALLOWED
    audit_entry: Optional[AuditLogEntry] = None


class Day2OperationsModule:
    """
    Enforces Day 2 operational constraints.
    
    Features:
    - Operation permission checking
    - Immutable audit logging
    - Restricted operation handling
    - Audit log export
    """
    
    # Operations allowed in Day 2
    ALLOWED_OPERATIONS = {
        OperationType.QUERY,
        OperationType.READ,
        OperationType.TOOL_EXECUTION,
        OperationType.NEW_PROJECT,
    }
    
    # Operations blocked in Day 2
    BLOCKED_OPERATIONS = {
        OperationType.BOOTSTRAP,
        OperationType.MEMORY_RESET,
        OperationType.CONFIG_CHANGE,
        OperationType.AGENT_INIT,
    }
    
    def __init__(self):
        """Initialize Day 2 operations module"""
        self.audit_log: List[AuditLogEntry] = []
        self._lock = threading.Lock()
        self._entry_counter = 0
        logger.debug("Day 2 Operations Module initialized")
    
    def check_operation_allowed(
        self,
        operation_type: OperationType,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Day2OperationResult:
        """
        Check if an operation is allowed in Day 2.
        
        Args:
            operation_type: Type of operation
            user_id: User performing the operation
            details: Additional operation details
            
        Returns:
            Day2OperationResult with permission status
        """
        details = details or {}
        
        # Check if operation is allowed
        if operation_type in self.ALLOWED_OPERATIONS:
            status = OperationStatus.ALLOWED
            reason = f"Operation {operation_type.value} is allowed in Day 2"
            allowed = True
        elif operation_type in self.BLOCKED_OPERATIONS:
            status = OperationStatus.BLOCKED
            reason = f"Operation {operation_type.value} is blocked in Day 2"
            allowed = False
        else:
            status = OperationStatus.RESTRICTED
            reason = f"Operation {operation_type.value} requires special handling"
            allowed = False
        
        # Create audit log entry
        audit_entry = self._create_audit_entry(
            operation_type=operation_type,
            status=status,
            user_id=user_id,
            details=details,
            error_message=None if allowed else reason,
        )
        
        # Log the operation
        logger.info(
            f"Day 2 operation check: {operation_type.value} - {status.value} "
            f"(user: {user_id})"
        )
        
        return Day2OperationResult(
            allowed=allowed,
            operation_type=operation_type,
            reason=reason,
            status=status,
            audit_entry=audit_entry,
        )
    
    def _create_audit_entry(
        self,
        operation_type: OperationType,
        status: OperationStatus,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Create and log an audit entry.
        
        Args:
            operation_type: Type of operation
            status: Operation status
            user_id: User performing the operation
            details: Additional details
            error_message: Error message if operation failed
            
        Returns:
            AuditLogEntry
        """
        with self._lock:
            self._entry_counter += 1
            entry_id = f"audit_{self._entry_counter:06d}"
            
            entry = AuditLogEntry(
                entry_id=entry_id,
                timestamp=time.time(),
                operation_type=operation_type,
                status=status,
                user_id=user_id,
                details=details or {},
                error_message=error_message,
            )
            
            # Add to immutable log
            self.audit_log.append(entry)
        
        return entry
    
    def get_audit_log(
        self,
        operation_type: Optional[OperationType] = None,
        status: Optional[OperationStatus] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLogEntry]:
        """
        Get audit log entries with optional filtering.
        
        Args:
            operation_type: Filter by operation type
            status: Filter by status
            user_id: Filter by user ID
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        with self._lock:
            entries = self.audit_log.copy()
        
        # Apply filters
        if operation_type:
            entries = [e for e in entries if e.operation_type == operation_type]
        if status:
            entries = [e for e in entries if e.status == status]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        
        # Apply limit
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def get_audit_log_count(self) -> int:
        """
        Get total number of audit log entries.
        
        Returns:
            Number of entries
        """
        with self._lock:
            return len(self.audit_log)
    
    def export_audit_log(self) -> List[Dict[str, Any]]:
        """
        Export audit log as list of dictionaries.
        
        Returns:
            List of audit log entries as dictionaries
        """
        with self._lock:
            entries = self.audit_log.copy()
        
        return [entry.to_dict() for entry in entries]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            entries = self.audit_log.copy()
        
        stats = {
            "total_entries": len(entries),
            "allowed_operations": len([e for e in entries if e.status == OperationStatus.ALLOWED]),
            "blocked_operations": len([e for e in entries if e.status == OperationStatus.BLOCKED]),
            "restricted_operations": len([e for e in entries if e.status == OperationStatus.RESTRICTED]),
            "operations_by_type": {},
            "operations_by_user": {},
        }
        
        # Count by operation type
        for op_type in OperationType:
            count = len([e for e in entries if e.operation_type == op_type])
            if count > 0:
                stats["operations_by_type"][op_type.value] = count
        
        # Count by user
        for entry in entries:
            if entry.user_id:
                if entry.user_id not in stats["operations_by_user"]:
                    stats["operations_by_user"][entry.user_id] = 0
                stats["operations_by_user"][entry.user_id] += 1
        
        return stats
    
    def clear_audit_log(self) -> None:
        """
        Clear audit log (use with caution - breaks immutability).
        
        Note: This should only be used in testing or during system reset.
        """
        with self._lock:
            self.audit_log.clear()
            self._entry_counter = 0
        
        logger.warning("Audit log cleared")
