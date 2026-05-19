"""Unit tests for trace_id_tracking module."""

import pytest
import time
import threading
from kabbalah.trace_id_tracking import (
    TraceIDGenerator,
    ExecutionLog,
    ExecutionLogEntry,
    TraceIDError,
    ExecutionLogError
)


class TestTraceIDGeneratorRunID:
    """Tests for run_id generation."""
    
    def test_generate_run_id_format(self):
        """Test that generated run_id has correct format."""
        run_id = TraceIDGenerator.generate_run_id()
        assert run_id.startswith("run_")
        parts = run_id.split("_")
        assert len(parts) == 5  # run, YYYY, MM, DD, NNN
        assert len(parts[1]) == 4  # YYYY
        assert len(parts[2]) == 2  # MM
        assert len(parts[3]) == 2  # DD
        assert len(parts[4]) >= 3  # NNN minimum
    
    def test_generate_run_id_uniqueness(self):
        """Test that generated run_ids are unique."""
        run_ids = set()
        for _ in range(10):
            run_id = TraceIDGenerator.generate_run_id()
            assert run_id not in run_ids
            run_ids.add(run_id)
    
    def test_generate_run_id_increments_counter(self):
        """Test that run_id counter increments."""
        run_id1 = TraceIDGenerator.generate_run_id()
        run_id2 = TraceIDGenerator.generate_run_id()
        
        # Extract counter from run_ids
        counter1 = int(run_id1.split("_")[-1])
        counter2 = int(run_id2.split("_")[-1])
        
        assert counter2 > counter1
    
    def test_validate_run_id_valid(self):
        """Test validation of valid run_id."""
        run_id = "run_2026_04_06_001"
        # Should not raise
        TraceIDGenerator._validate_run_id(run_id)
    
    def test_validate_run_id_invalid_format(self):
        """Test validation rejects invalid run_id format."""
        invalid_ids = [
            "run_2026_4_6_001",  # Single digit month/day
            "run_2026_04_06_01",  # Two digit counter
            "run_2026_04_06",  # Missing counter
            "run_26_04_06_001",  # Two digit year
            "invalid_2026_04_06_001",  # Wrong prefix
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(TraceIDError):
                TraceIDGenerator._validate_run_id(invalid_id)
    
    def test_validate_run_id_null(self):
        """Test validation rejects null run_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator._validate_run_id(None)
    
    def test_validate_run_id_empty(self):
        """Test validation rejects empty run_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator._validate_run_id("")


class TestTraceIDGeneratorBranchID:
    """Tests for branch_id generation."""
    
    def test_generate_branch_id_format(self):
        """Test that generated branch_id has correct format."""
        branch_id = TraceIDGenerator.generate_branch_id("backend")
        assert branch_id.startswith("branch_backend_")
        parts = branch_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "branch"
        assert parts[1] == "backend"
        assert len(parts[2]) >= 3  # NNN minimum
    
    def test_generate_branch_id_multiple_domains(self):
        """Test branch_id generation for multiple domains."""
        backend_id = TraceIDGenerator.generate_branch_id("backend")
        frontend_id = TraceIDGenerator.generate_branch_id("frontend")
        
        assert "backend" in backend_id
        assert "frontend" in frontend_id
        assert backend_id != frontend_id
    
    def test_generate_branch_id_uniqueness_per_domain(self):
        """Test that branch_ids are unique per domain."""
        ids = set()
        for _ in range(5):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            assert branch_id not in ids
            ids.add(branch_id)
    
    def test_generate_branch_id_invalid_domain(self):
        """Test branch_id generation rejects invalid domain."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator.generate_branch_id(None)
        
        with pytest.raises(TraceIDError):
            TraceIDGenerator.generate_branch_id("")
    
    def test_validate_branch_id_valid(self):
        """Test validation of valid branch_id."""
        branch_id = "branch_backend_001"
        # Should not raise
        TraceIDGenerator._validate_branch_id(branch_id)
    
    def test_validate_branch_id_invalid_format(self):
        """Test validation rejects invalid branch_id format."""
        invalid_ids = [
            "branch_backend_01",  # Two digit counter
            "branch_backend",  # Missing counter
            "invalid_backend_001",  # Wrong prefix
            "branch_001",  # Missing domain
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(TraceIDError):
                TraceIDGenerator._validate_branch_id(invalid_id)


class TestTraceIDGeneratorLeafID:
    """Tests for leaf_id generation."""
    
    def test_generate_leaf_id_format(self):
        """Test that generated leaf_id has correct format."""
        leaf_id = TraceIDGenerator.generate_leaf_id("backend")
        assert leaf_id.startswith("leaf_backend_")
        parts = leaf_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "leaf"
        assert parts[1] == "backend"
        assert len(parts[2]) >= 3  # NNN minimum
    
    def test_generate_leaf_id_uniqueness_per_domain(self):
        """Test that leaf_ids are unique per domain."""
        ids = set()
        for _ in range(5):
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            assert leaf_id not in ids
            ids.add(leaf_id)
    
    def test_generate_leaf_id_multiple_domains(self):
        """Test leaf_id generation for multiple domains."""
        backend_id = TraceIDGenerator.generate_leaf_id("backend")
        frontend_id = TraceIDGenerator.generate_leaf_id("frontend")
        
        assert "backend" in backend_id
        assert "frontend" in frontend_id
        assert backend_id != frontend_id
    
    def test_validate_leaf_id_valid(self):
        """Test validation of valid leaf_id."""
        leaf_id = "leaf_backend_001"
        # Should not raise
        TraceIDGenerator._validate_leaf_id(leaf_id)
    
    def test_validate_leaf_id_invalid_format(self):
        """Test validation rejects invalid leaf_id format."""
        invalid_ids = [
            "leaf_backend_01",  # Two digit counter
            "leaf_backend",  # Missing counter
            "invalid_backend_001",  # Wrong prefix
            "leaf_001",  # Missing domain
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(TraceIDError):
                TraceIDGenerator._validate_leaf_id(invalid_id)


class TestTraceIDConstruction:
    """Tests for trace_id construction."""
    
    def test_construct_trace_id_valid(self):
        """Test construction of valid trace_id."""
        run_id = "run_2026_04_06_001"
        branch_id = "branch_backend_001"
        leaf_id = "leaf_backend_001"
        
        trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
        
        assert trace_id == f"{run_id}:{branch_id}:{leaf_id}"
    
    def test_construct_trace_id_format(self):
        """Test that constructed trace_id has correct format."""
        run_id = TraceIDGenerator.generate_run_id()
        branch_id = TraceIDGenerator.generate_branch_id("backend")
        leaf_id = TraceIDGenerator.generate_leaf_id("backend")
        
        trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
        
        parts = trace_id.split(":")
        assert len(parts) == 3
        assert parts[0] == run_id
        assert parts[1] == branch_id
        assert parts[2] == leaf_id
    
    def test_construct_trace_id_invalid_run_id(self):
        """Test construction rejects invalid run_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator.construct_trace_id(
                "invalid_run_id",
                "branch_backend_001",
                "leaf_backend_001"
            )
    
    def test_construct_trace_id_invalid_branch_id(self):
        """Test construction rejects invalid branch_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator.construct_trace_id(
                "run_2026_04_06_001",
                "invalid_branch_id",
                "leaf_backend_001"
            )
    
    def test_construct_trace_id_invalid_leaf_id(self):
        """Test construction rejects invalid leaf_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator.construct_trace_id(
                "run_2026_04_06_001",
                "branch_backend_001",
                "invalid_leaf_id"
            )
    
    def test_validate_trace_id_valid(self):
        """Test validation of valid trace_id."""
        trace_id = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        # Should not raise
        TraceIDGenerator._validate_trace_id(trace_id)
    
    def test_validate_trace_id_invalid_format(self):
        """Test validation rejects invalid trace_id format."""
        invalid_ids = [
            "run_2026_04_06_001:branch_backend_001",  # Missing leaf_id
            "run_2026_04_06_001",  # Missing branch_id and leaf_id
            "run_2026_04_06_001:branch_backend_001:leaf_backend_001:extra",  # Extra part
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(TraceIDError):
                TraceIDGenerator._validate_trace_id(invalid_id)
    
    def test_parse_trace_id_valid(self):
        """Test parsing of valid trace_id."""
        run_id = "run_2026_04_06_001"
        branch_id = "branch_backend_001"
        leaf_id = "leaf_backend_001"
        trace_id = f"{run_id}:{branch_id}:{leaf_id}"
        
        parsed_run, parsed_branch, parsed_leaf = TraceIDGenerator.parse_trace_id(trace_id)
        
        assert parsed_run == run_id
        assert parsed_branch == branch_id
        assert parsed_leaf == leaf_id
    
    def test_parse_trace_id_invalid(self):
        """Test parsing rejects invalid trace_id."""
        with pytest.raises(TraceIDError):
            TraceIDGenerator.parse_trace_id("invalid_trace_id")


class TestExecutionLogEntry:
    """Tests for ExecutionLogEntry immutability."""
    
    def test_entry_immutability(self):
        """Test that ExecutionLogEntry is immutable after creation."""
        entry = ExecutionLogEntry(
            trace_id="run_2026_04_06_001:branch_backend_001:leaf_backend_001",
            operation_name="test_op",
            operation_type="write",
            status="success",
            start_time=time.time(),
            end_time=time.time() + 1,
            duration=1.0
        )
        
        # Attempt to modify should raise error
        with pytest.raises(ExecutionLogError):
            entry.operation_name = "modified"
    
    def test_entry_creation_with_defaults(self):
        """Test ExecutionLogEntry creation with default values."""
        start_time = time.time()
        end_time = start_time + 1
        
        entry = ExecutionLogEntry(
            trace_id="run_2026_04_06_001:branch_backend_001:leaf_backend_001",
            operation_name="test_op",
            operation_type="write",
            status="success",
            start_time=start_time,
            end_time=end_time
        )
        
        assert entry.inputs == {}
        assert entry.outputs == {}
        assert entry.metadata == {}
        assert entry.duration == 1.0


class TestExecutionLog:
    """Tests for ExecutionLog functionality."""
    
    def test_append_entry_valid(self):
        """Test appending valid entry to log."""
        log = ExecutionLog()
        trace_id = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        
        entry = log.append_entry(
            trace_id=trace_id,
            operation_name="test_op",
            operation_type="write",
            status="success",
            start_time=time.time(),
            end_time=time.time() + 1
        )
        
        assert entry.trace_id == trace_id
        assert entry.operation_name == "test_op"
        assert entry.operation_type == "write"
        assert entry.status == "success"
    
    def test_append_entry_invalid_trace_id(self):
        """Test appending entry with invalid trace_id."""
        log = ExecutionLog()
        
        with pytest.raises(ExecutionLogError):
            log.append_entry(
                trace_id="invalid_trace_id",
                operation_name="test_op",
                operation_type="write",
                status="success",
                start_time=time.time(),
                end_time=time.time() + 1
            )
    
    def test_append_entry_invalid_operation_type(self):
        """Test appending entry with invalid operation_type."""
        log = ExecutionLog()
        trace_id = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        
        with pytest.raises(ExecutionLogError):
            log.append_entry(
                trace_id=trace_id,
                operation_name="test_op",
                operation_type="invalid_type",
                status="success",
                start_time=time.time(),
                end_time=time.time() + 1
            )
    
    def test_append_entry_invalid_status(self):
        """Test appending entry with invalid status."""
        log = ExecutionLog()
        trace_id = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        
        with pytest.raises(ExecutionLogError):
            log.append_entry(
                trace_id=trace_id,
                operation_name="test_op",
                operation_type="write",
                status="invalid_status",
                start_time=time.time(),
                end_time=time.time() + 1
            )
    
    def test_get_entries_by_trace_id(self):
        """Test retrieving entries by trace_id."""
        log = ExecutionLog()
        trace_id = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        
        log.append_entry(trace_id, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id, "op2", "read", "success", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_trace_id(trace_id)
        
        assert len(entries) == 2
        assert entries[0].operation_name == "op1"
        assert entries[1].operation_name == "op2"
    
    def test_get_entries_by_run_id(self):
        """Test retrieving entries by run_id."""
        log = ExecutionLog()
        run_id = "run_2026_04_06_001"
        trace_id1 = f"{run_id}:branch_backend_001:leaf_backend_001"
        trace_id2 = f"{run_id}:branch_frontend_001:leaf_frontend_001"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "read", "success", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_run_id(run_id)
        
        assert len(entries) == 2
    
    def test_get_entries_by_branch_id(self):
        """Test retrieving entries by branch_id."""
        log = ExecutionLog()
        run_id = "run_2026_04_06_001"
        branch_id = "branch_backend_001"
        trace_id1 = f"{run_id}:{branch_id}:leaf_backend_001"
        trace_id2 = f"{run_id}:{branch_id}:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "read", "success", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_branch_id(branch_id)
        
        assert len(entries) == 2
    
    def test_get_entries_by_leaf_id(self):
        """Test retrieving entries by leaf_id."""
        log = ExecutionLog()
        run_id = "run_2026_04_06_001"
        leaf_id = "leaf_backend_001"
        trace_id1 = f"{run_id}:branch_backend_001:{leaf_id}"
        trace_id2 = f"{run_id}:branch_backend_002:{leaf_id}"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "read", "success", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_leaf_id(leaf_id)
        
        assert len(entries) == 2
    
    def test_get_entries_by_operation_type(self):
        """Test retrieving entries by operation_type."""
        log = ExecutionLog()
        trace_id1 = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        trace_id2 = "run_2026_04_06_001:branch_backend_002:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "write", "success", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_operation_type("write")
        
        assert len(entries) == 2
        assert all(e.operation_type == "write" for e in entries)
    
    def test_get_entries_by_status(self):
        """Test retrieving entries by status."""
        log = ExecutionLog()
        trace_id1 = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        trace_id2 = "run_2026_04_06_001:branch_backend_002:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "write", "error", time.time(), time.time() + 1)
        
        entries = log.get_entries_by_status("success")
        
        assert len(entries) == 1
        assert entries[0].status == "success"
    
    def test_get_all_entries(self):
        """Test retrieving all entries."""
        log = ExecutionLog()
        trace_id1 = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        trace_id2 = "run_2026_04_06_001:branch_backend_002:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op2", "read", "success", time.time(), time.time() + 1)
        
        entries = log.get_all_entries()
        
        assert len(entries) == 2
    
    def test_get_entry_count(self):
        """Test getting total entry count."""
        log = ExecutionLog()
        trace_id1 = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        trace_id2 = "run_2026_04_06_001:branch_backend_002:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id1, "op2", "read", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op3", "write", "success", time.time(), time.time() + 1)
        
        assert log.get_entry_count() == 3
    
    def test_get_trace_count(self):
        """Test getting unique trace_id count."""
        log = ExecutionLog()
        trace_id1 = "run_2026_04_06_001:branch_backend_001:leaf_backend_001"
        trace_id2 = "run_2026_04_06_001:branch_backend_002:leaf_backend_002"
        
        log.append_entry(trace_id1, "op1", "write", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id1, "op2", "read", "success", time.time(), time.time() + 1)
        log.append_entry(trace_id2, "op3", "write", "success", time.time(), time.time() + 1)
        
        assert log.get_trace_count() == 2
    
    def test_thread_safety(self):
        """Test that ExecutionLog is thread-safe."""
        log = ExecutionLog()
        errors = []
        
        def append_entries(thread_id):
            try:
                for i in range(10):
                    trace_id = f"run_2026_04_06_001:branch_backend_{thread_id:03d}:leaf_backend_{i:03d}"
                    log.append_entry(
                        trace_id,
                        f"op_{thread_id}_{i}",
                        "write",
                        "success",
                        time.time(),
                        time.time() + 1
                    )
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=append_entries, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert log.get_entry_count() == 50
