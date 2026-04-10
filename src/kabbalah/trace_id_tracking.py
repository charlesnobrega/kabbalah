"""Hierarchical Run_ID Tracking - Complete traceability of all operations."""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import threading


class TraceIDError(Exception):
    """Raised when trace_id generation or validation fails."""
    pass


class ExecutionLogError(Exception):
    """Raised when execution log operations fail."""
    pass


@dataclass
class ExecutionLogEntry:
    """Immutable entry in the execution log."""
    trace_id: str
    operation_name: str
    operation_type: str  # bootstrap, query, read, write, tool_execution
    status: str  # success, error, timeout, blocked
    start_time: float
    end_time: float
    duration: float
    inputs: Dict = field(default_factory=dict)
    outputs: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    
    def __setattr__(self, name, value):
        """Prevent modification after creation (immutability)."""
        if hasattr(self, '_initialized'):
            raise ExecutionLogError(f"Cannot modify immutable ExecutionLogEntry field: {name}")
        super().__setattr__(name, value)
    
    def __post_init__(self):
        """Mark as initialized to enforce immutability."""
        object.__setattr__(self, '_initialized', True)


class TraceIDGenerator:
    """Generates unique trace_ids with hierarchical structure."""
    
    # Thread-safe counters for generating unique IDs
    _run_counter = 0
    _branch_counters = {}
    _leaf_counters = {}
    _last_date = None
    _lock = threading.Lock()
    
    @classmethod
    def generate_run_id(cls) -> str:
        """
        Generate a unique run_id with format "run_YYYY_MM_DD_NNN".
        
        Returns:
            Unique run_id string
            
        Raises:
            TraceIDError: If generation fails
        """
        try:
            with cls._lock:
                now = datetime.utcnow()
                date_str = now.strftime("%Y_%m_%d")
                
                # Reset counter if date changed
                if date_str != cls._last_date:
                    cls._last_date = date_str
                    cls._run_counter = 0
                
                # Increment counter
                cls._run_counter += 1
                counter_str = str(cls._run_counter).zfill(3)
                
                run_id = f"run_{date_str}_{counter_str}"
                return run_id
        except Exception as e:
            raise TraceIDError(f"Failed to generate run_id: {str(e)}")
    
    @classmethod
    def generate_branch_id(cls, domain: str) -> str:
        """
        Generate a unique branch_id with format "branch_{domain}_{NNN}".
        
        Args:
            domain: Domain name
            
        Returns:
            Unique branch_id string
            
        Raises:
            TraceIDError: If generation fails or domain is invalid
        """
        try:
            if not domain or not isinstance(domain, str):
                raise TraceIDError("Domain must be a non-empty string")
            
            with cls._lock:
                now = datetime.utcnow()
                date_str = now.strftime("%Y_%m_%d")
                
                # Reset counters if date changed
                if date_str != cls._last_date:
                    cls._last_date = date_str
                    cls._branch_counters = {}
                    cls._leaf_counters = {}
                
                # Get counter for this domain
                if domain not in cls._branch_counters:
                    cls._branch_counters[domain] = 0
                
                cls._branch_counters[domain] += 1
                counter = cls._branch_counters[domain]
                
                branch_id = f"branch_{domain}_{counter:03d}"
                return branch_id
        except TraceIDError:
            raise
        except Exception as e:
            raise TraceIDError(f"Failed to generate branch_id: {str(e)}")
    
    @classmethod
    def generate_leaf_id(cls, domain: str) -> str:
        """
        Generate a unique leaf_id with format "leaf_{domain}_{NNN}".
        
        Args:
            domain: Domain name
            
        Returns:
            Unique leaf_id string
            
        Raises:
            TraceIDError: If generation fails or domain is invalid
        """
        try:
            if not domain or not isinstance(domain, str):
                raise TraceIDError("Domain must be a non-empty string")
            
            with cls._lock:
                now = datetime.utcnow()
                date_str = now.strftime("%Y_%m_%d")
                
                # Reset counters if date changed
                if date_str != cls._last_date:
                    cls._last_date = date_str
                    cls._branch_counters = {}
                    cls._leaf_counters = {}
                
                # Get counter for this domain
                if domain not in cls._leaf_counters:
                    cls._leaf_counters[domain] = 0
                
                cls._leaf_counters[domain] += 1
                counter = cls._leaf_counters[domain]
                
                leaf_id = f"leaf_{domain}_{counter:03d}"
                return leaf_id
        except TraceIDError:
            raise
        except Exception as e:
            raise TraceIDError(f"Failed to generate leaf_id: {str(e)}")
    
    @classmethod
    def construct_trace_id(cls, run_id: str, branch_id: str, leaf_id: str) -> str:
        """
        Construct a hierarchical trace_id from components.
        
        Format: run_id:branch_id:leaf_id
        
        Args:
            run_id: Run identifier
            branch_id: Branch identifier
            leaf_id: Leaf identifier
            
        Returns:
            Hierarchical trace_id string
            
        Raises:
            TraceIDError: If any component is invalid
        """
        try:
            # Validate components
            cls._validate_run_id(run_id)
            cls._validate_branch_id(branch_id)
            cls._validate_leaf_id(leaf_id)
            
            trace_id = f"{run_id}:{branch_id}:{leaf_id}"
            
            # Validate constructed trace_id
            cls._validate_trace_id(trace_id)
            
            return trace_id
        except TraceIDError:
            raise
        except Exception as e:
            raise TraceIDError(f"Failed to construct trace_id: {str(e)}")
    
    @classmethod
    def _validate_run_id(cls, run_id: str) -> None:
        """Validate run_id format."""
        if not run_id or not isinstance(run_id, str):
            raise TraceIDError("run_id must be a non-empty string")
        
        pattern = r"^run_\d{4}_\d{2}_\d{2}_\d{3}$"
        if not re.match(pattern, run_id):
            raise TraceIDError(f"Invalid run_id format: {run_id}. Expected: run_YYYY_MM_DD_NNN")
    
    @classmethod
    def _validate_branch_id(cls, branch_id: str) -> None:
        """Validate branch_id format."""
        if not branch_id or not isinstance(branch_id, str):
            raise TraceIDError("branch_id must be a non-empty string")
        
        pattern = r"^branch_[a-zA-Z0-9_]+_\d{3}$"
        if not re.match(pattern, branch_id):
            raise TraceIDError(f"Invalid branch_id format: {branch_id}. Expected: branch_{{domain}}_NNN")
    
    @classmethod
    def _validate_leaf_id(cls, leaf_id: str) -> None:
        """Validate leaf_id format."""
        if not leaf_id or not isinstance(leaf_id, str):
            raise TraceIDError("leaf_id must be a non-empty string")
        
        pattern = r"^leaf_[a-zA-Z0-9_]+_\d{3}$"
        if not re.match(pattern, leaf_id):
            raise TraceIDError(f"Invalid leaf_id format: {leaf_id}. Expected: leaf_{{domain}}_NNN")
    
    @classmethod
    def _validate_trace_id(cls, trace_id: str) -> None:
        """Validate trace_id format."""
        if not trace_id or not isinstance(trace_id, str):
            raise TraceIDError("trace_id must be a non-empty string")
        
        parts = trace_id.split(":")
        if len(parts) != 3:
            raise TraceIDError(f"Invalid trace_id format: {trace_id}. Expected: run_id:branch_id:leaf_id")
        
        cls._validate_run_id(parts[0])
        cls._validate_branch_id(parts[1])
        cls._validate_leaf_id(parts[2])
    
    @classmethod
    def parse_trace_id(cls, trace_id: str) -> Tuple[str, str, str]:
        """
        Parse a trace_id into its components.
        
        Args:
            trace_id: Hierarchical trace identifier
            
        Returns:
            Tuple of (run_id, branch_id, leaf_id)
            
        Raises:
            TraceIDError: If trace_id is invalid
        """
        try:
            cls._validate_trace_id(trace_id)
            parts = trace_id.split(":")
            return parts[0], parts[1], parts[2]
        except TraceIDError:
            raise
        except Exception as e:
            raise TraceIDError(f"Failed to parse trace_id: {str(e)}")


class ExecutionLog:
    """Immutable execution log indexed by trace_id for complete auditability."""
    
    def __init__(self):
        """Initialize ExecutionLog."""
        self._entries: Dict[str, List[ExecutionLogEntry]] = {}
        self._lock = threading.Lock()
    
    def append_entry(
        self,
        trace_id: str,
        operation_name: str,
        operation_type: str,
        status: str,
        start_time: float,
        end_time: float,
        inputs: Optional[Dict] = None,
        outputs: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> ExecutionLogEntry:
        """
        Append an immutable entry to the execution log.
        
        Args:
            trace_id: Hierarchical trace identifier
            operation_name: Name of the operation
            operation_type: Type of operation (bootstrap, query, read, write, tool_execution)
            status: Operation status (success, error, timeout, blocked)
            start_time: Operation start timestamp
            end_time: Operation end timestamp
            inputs: Operation inputs (optional)
            outputs: Operation outputs (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            The created ExecutionLogEntry
            
        Raises:
            ExecutionLogError: If entry creation fails
        """
        try:
            # Validate trace_id
            TraceIDGenerator._validate_trace_id(trace_id)
            
            # Validate operation type
            valid_types = {"bootstrap", "query", "read", "write", "tool_execution"}
            if operation_type not in valid_types:
                raise ExecutionLogError(f"Invalid operation_type: {operation_type}")
            
            # Validate status
            valid_statuses = {"success", "error", "timeout", "blocked"}
            if status not in valid_statuses:
                raise ExecutionLogError(f"Invalid status: {status}")
            
            # Create immutable entry
            duration = end_time - start_time
            entry = ExecutionLogEntry(
                trace_id=trace_id,
                operation_name=operation_name,
                operation_type=operation_type,
                status=status,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                inputs=inputs or {},
                outputs=outputs or {},
                metadata=metadata or {}
            )
            
            # Append to log (thread-safe)
            with self._lock:
                if trace_id not in self._entries:
                    self._entries[trace_id] = []
                self._entries[trace_id].append(entry)
            
            return entry
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to append entry: {str(e)}")
    
    def get_entries_by_trace_id(self, trace_id: str) -> List[ExecutionLogEntry]:
        """
        Get all entries for a specific trace_id.
        
        Args:
            trace_id: Hierarchical trace identifier
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If trace_id is invalid
        """
        try:
            TraceIDGenerator._validate_trace_id(trace_id)
            
            with self._lock:
                return self._entries.get(trace_id, [])
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries: {str(e)}")
    
    def get_entries_by_run_id(self, run_id: str) -> List[ExecutionLogEntry]:
        """
        Get all entries for a specific run_id.
        
        Args:
            run_id: Run identifier
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If run_id is invalid
        """
        try:
            TraceIDGenerator._validate_run_id(run_id)
            
            entries = []
            with self._lock:
                for trace_id, trace_entries in self._entries.items():
                    if trace_id.startswith(run_id + ":"):
                        entries.extend(trace_entries)
            
            return entries
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries by run_id: {str(e)}")
    
    def get_entries_by_branch_id(self, branch_id: str) -> List[ExecutionLogEntry]:
        """
        Get all entries for a specific branch_id.
        
        Args:
            branch_id: Branch identifier
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If branch_id is invalid
        """
        try:
            TraceIDGenerator._validate_branch_id(branch_id)
            
            entries = []
            with self._lock:
                for trace_id, trace_entries in self._entries.items():
                    parts = trace_id.split(":")
                    if len(parts) == 3 and parts[1] == branch_id:
                        entries.extend(trace_entries)
            
            return entries
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries by branch_id: {str(e)}")
    
    def get_entries_by_leaf_id(self, leaf_id: str) -> List[ExecutionLogEntry]:
        """
        Get all entries for a specific leaf_id.
        
        Args:
            leaf_id: Leaf identifier
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If leaf_id is invalid
        """
        try:
            TraceIDGenerator._validate_leaf_id(leaf_id)
            
            entries = []
            with self._lock:
                for trace_id, trace_entries in self._entries.items():
                    parts = trace_id.split(":")
                    if len(parts) == 3 and parts[2] == leaf_id:
                        entries.extend(trace_entries)
            
            return entries
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries by leaf_id: {str(e)}")
    
    def get_entries_by_operation_type(self, operation_type: str) -> List[ExecutionLogEntry]:
        """
        Get all entries for a specific operation type.
        
        Args:
            operation_type: Type of operation (bootstrap, query, read, write, tool_execution)
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If operation_type is invalid
        """
        try:
            valid_types = {"bootstrap", "query", "read", "write", "tool_execution"}
            if operation_type not in valid_types:
                raise ExecutionLogError(f"Invalid operation_type: {operation_type}")
            
            entries = []
            with self._lock:
                for trace_entries in self._entries.values():
                    entries.extend([e for e in trace_entries if e.operation_type == operation_type])
            
            return entries
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries by operation_type: {str(e)}")
    
    def get_entries_by_status(self, status: str) -> List[ExecutionLogEntry]:
        """
        Get all entries with a specific status.
        
        Args:
            status: Operation status (success, error, timeout, blocked)
            
        Returns:
            List of ExecutionLogEntry objects
            
        Raises:
            ExecutionLogError: If status is invalid
        """
        try:
            valid_statuses = {"success", "error", "timeout", "blocked"}
            if status not in valid_statuses:
                raise ExecutionLogError(f"Invalid status: {status}")
            
            entries = []
            with self._lock:
                for trace_entries in self._entries.values():
                    entries.extend([e for e in trace_entries if e.status == status])
            
            return entries
        except ExecutionLogError:
            raise
        except Exception as e:
            raise ExecutionLogError(f"Failed to get entries by status: {str(e)}")
    
    def get_all_entries(self) -> List[ExecutionLogEntry]:
        """
        Get all entries in the execution log.
        
        Returns:
            List of all ExecutionLogEntry objects
        """
        with self._lock:
            entries = []
            for trace_entries in self._entries.values():
                entries.extend(trace_entries)
            return entries
    
    def get_entry_count(self) -> int:
        """
        Get total number of entries in the execution log.
        
        Returns:
            Total entry count
        """
        with self._lock:
            return sum(len(entries) for entries in self._entries.values())
    
    def get_trace_count(self) -> int:
        """
        Get number of unique trace_ids in the execution log.
        
        Returns:
            Number of unique trace_ids
        """
        with self._lock:
            return len(self._entries)
