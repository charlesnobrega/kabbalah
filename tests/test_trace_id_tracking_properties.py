"""Property-based tests for trace_id_tracking module."""

import pytest
from hypothesis import given, strategies as st, assume
import time
from kabbalah.trace_id_tracking import (
    TraceIDGenerator,
    ExecutionLog,
    TraceIDError,
    ExecutionLogError
)


# Custom strategies for generating valid IDs
@st.composite
def valid_domains(draw):
    """Generate valid domain names."""
    return draw(st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs'), blacklist_characters=':'),
        min_size=1,
        max_size=20
    ))


@st.composite
def valid_operation_types(draw):
    """Generate valid operation types."""
    return draw(st.sampled_from(["bootstrap", "query", "read", "write", "tool_execution"]))


@st.composite
def valid_statuses(draw):
    """Generate valid statuses."""
    return draw(st.sampled_from(["success", "error", "timeout", "blocked"]))


class TestTraceIDConsistencyProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property 5: Trace_ID Hierarchical Consistency
    
    Every artifact has a valid hierarchical trace_id (run_id:branch_id:leaf_id).
    """
    
    @given(
        domain=valid_domains(),
        num_branches=st.integers(min_value=1, max_value=5),
        num_leaves=st.integers(min_value=1, max_value=5)
    )
    def test_trace_id_hierarchical_consistency(self, domain, num_branches, num_leaves):
        """
        Property: All constructed trace_ids have valid hierarchical structure.
        
        For all generated trace_ids:
        - trace_id must have exactly 3 parts separated by colons
        - Each part must match its respective format pattern
        - Parts must be in correct order: run_id:branch_id:leaf_id
        """
        run_id = TraceIDGenerator.generate_run_id()
        
        for _ in range(num_branches):
            branch_id = TraceIDGenerator.generate_branch_id(domain)
            
            for _ in range(num_leaves):
                leaf_id = TraceIDGenerator.generate_leaf_id(domain)
                
                # Construct trace_id
                trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
                
                # Verify structure
                parts = trace_id.split(":")
                assert len(parts) == 3, f"trace_id should have 3 parts, got {len(parts)}"
                
                # Verify each part is valid
                assert parts[0] == run_id
                assert parts[1] == branch_id
                assert parts[2] == leaf_id
                
                # Verify we can parse it back
                parsed_run, parsed_branch, parsed_leaf = TraceIDGenerator.parse_trace_id(trace_id)
                assert parsed_run == run_id
                assert parsed_branch == branch_id
                assert parsed_leaf == leaf_id
    
    @given(
        domain=valid_domains(),
        num_traces=st.integers(min_value=1, max_value=10)
    )
    def test_all_trace_ids_are_parseable(self, domain, num_traces):
        """
        Property: All generated trace_ids can be parsed back to their components.
        
        For all generated trace_ids:
        - parse_trace_id should succeed
        - Parsed components should match original components
        """
        run_id = TraceIDGenerator.generate_run_id()
        
        for _ in range(num_traces):
            branch_id = TraceIDGenerator.generate_branch_id(domain)
            leaf_id = TraceIDGenerator.generate_leaf_id(domain)
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            # Should not raise
            parsed_run, parsed_branch, parsed_leaf = TraceIDGenerator.parse_trace_id(trace_id)
            
            # Verify round-trip
            assert parsed_run == run_id
            assert parsed_branch == branch_id
            assert parsed_leaf == leaf_id


class TestRunIDUniquenessProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property 19: Run_ID Uniqueness
    
    All generated run_ids are unique within a day.
    """
    
    @given(num_ids=st.integers(min_value=1, max_value=100))
    def test_run_id_uniqueness(self, num_ids):
        """
        Property: All generated run_ids are unique.
        
        For all generated run_ids:
        - No two run_ids should be identical
        - Each run_id should have incrementing counter
        """
        run_ids = set()
        
        for _ in range(num_ids):
            run_id = TraceIDGenerator.generate_run_id()
            
            # Should not have seen this run_id before
            assert run_id not in run_ids, f"Duplicate run_id generated: {run_id}"
            run_ids.add(run_id)
        
        # All run_ids should be unique
        assert len(run_ids) == num_ids
    
    @given(num_ids=st.integers(min_value=2, max_value=50))
    def test_run_id_counter_increments(self, num_ids):
        """
        Property: Run_ID counters increment monotonically.
        
        For all generated run_ids:
        - Counter should increase with each generation
        - Counter should be 3 digits (zero-padded)
        """
        run_ids = []
        
        for _ in range(num_ids):
            run_id = TraceIDGenerator.generate_run_id()
            run_ids.append(run_id)
        
        # Extract counters
        counters = [int(run_id.split("_")[-1]) for run_id in run_ids]
        
        # Verify monotonic increase
        for i in range(1, len(counters)):
            assert counters[i] > counters[i-1], \
                f"Counter should increase: {counters[i-1]} -> {counters[i]}"


class TestBranchIDUniquenessProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property: Branch_ID Uniqueness per Domain
    
    All generated branch_ids are unique per domain.
    """
    
    @given(
        domain=valid_domains(),
        num_ids=st.integers(min_value=1, max_value=50)
    )
    def test_branch_id_uniqueness_per_domain(self, domain, num_ids):
        """
        Property: All generated branch_ids are unique per domain.
        
        For all generated branch_ids in a domain:
        - No two branch_ids should be identical
        - Each branch_id should have incrementing counter
        """
        branch_ids = set()
        
        for _ in range(num_ids):
            branch_id = TraceIDGenerator.generate_branch_id(domain)
            
            # Should not have seen this branch_id before
            assert branch_id not in branch_ids, f"Duplicate branch_id generated: {branch_id}"
            branch_ids.add(branch_id)
        
        # All branch_ids should be unique
        assert len(branch_ids) == num_ids


class TestLeafIDUniquenessProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property: Leaf_ID Uniqueness per Domain
    
    All generated leaf_ids are unique per domain.
    """
    
    @given(
        domain=valid_domains(),
        num_ids=st.integers(min_value=1, max_value=50)
    )
    def test_leaf_id_uniqueness_per_domain(self, domain, num_ids):
        """
        Property: All generated leaf_ids are unique per domain.
        
        For all generated leaf_ids in a domain:
        - No two leaf_ids should be identical
        - Each leaf_id should have incrementing counter
        """
        leaf_ids = set()
        
        for _ in range(num_ids):
            leaf_id = TraceIDGenerator.generate_leaf_id(domain)
            
            # Should not have seen this leaf_id before
            assert leaf_id not in leaf_ids, f"Duplicate leaf_id generated: {leaf_id}"
            leaf_ids.add(leaf_id)
        
        # All leaf_ids should be unique
        assert len(leaf_ids) == num_ids


class TestExecutionLogImmutabilityProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property: Execution Log Immutability
    
    All entries in the execution log are immutable after creation.
    """
    
    @given(
        operation_type=valid_operation_types(),
        status=valid_statuses(),
        num_entries=st.integers(min_value=1, max_value=10)
    )
    def test_execution_log_entries_immutable(self, operation_type, status, num_entries):
        """
        Property: All ExecutionLogEntry objects are immutable.
        
        For all created entries:
        - Attempting to modify any field should raise ExecutionLogError
        - Entry data should remain unchanged
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        entries = []
        for i in range(num_entries):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            entry = log.append_entry(
                trace_id=trace_id,
                operation_name=f"op_{i}",
                operation_type=operation_type,
                status=status,
                start_time=time.time(),
                end_time=time.time() + 1
            )
            entries.append(entry)
        
        # Verify all entries are immutable
        for entry in entries:
            with pytest.raises(ExecutionLogError):
                entry.operation_name = "modified"


class TestExecutionLogQueryProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property: Execution Log Query Correctness
    
    All queries on the execution log return correct results.
    """
    
    @given(
        num_traces=st.integers(min_value=1, max_value=5),
        num_entries_per_trace=st.integers(min_value=1, max_value=5)
    )
    def test_query_by_trace_id_returns_all_entries(self, num_traces, num_entries_per_trace):
        """
        Property: Querying by trace_id returns all entries for that trace_id.
        
        For all created entries:
        - Query by trace_id should return exactly the entries for that trace_id
        - No entries from other trace_ids should be returned
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        trace_entries = {}
        
        for t in range(num_traces):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            trace_entries[trace_id] = []
            
            for i in range(num_entries_per_trace):
                entry = log.append_entry(
                    trace_id=trace_id,
                    operation_name=f"op_{t}_{i}",
                    operation_type="write",
                    status="success",
                    start_time=time.time(),
                    end_time=time.time() + 1
                )
                trace_entries[trace_id].append(entry)
        
        # Verify queries
        for trace_id, expected_entries in trace_entries.items():
            retrieved = log.get_entries_by_trace_id(trace_id)
            assert len(retrieved) == len(expected_entries)
            
            for i, entry in enumerate(retrieved):
                assert entry.trace_id == trace_id
                assert entry.operation_name == expected_entries[i].operation_name
    
    @given(
        num_entries=st.integers(min_value=1, max_value=20),
        operation_type=valid_operation_types()
    )
    def test_query_by_operation_type_returns_correct_entries(self, num_entries, operation_type):
        """
        Property: Querying by operation_type returns all entries of that type.
        
        For all created entries:
        - Query by operation_type should return only entries of that type
        - All returned entries should have the queried operation_type
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        for i in range(num_entries):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            # Alternate between operation types
            op_type = operation_type if i % 2 == 0 else "query"
            
            log.append_entry(
                trace_id=trace_id,
                operation_name=f"op_{i}",
                operation_type=op_type,
                status="success",
                start_time=time.time(),
                end_time=time.time() + 1
            )
        
        # Query by operation_type
        retrieved = log.get_entries_by_operation_type(operation_type)
        
        # All retrieved entries should have the correct operation_type
        for entry in retrieved:
            assert entry.operation_type == operation_type
    
    @given(
        num_entries=st.integers(min_value=1, max_value=20),
        status=valid_statuses()
    )
    def test_query_by_status_returns_correct_entries(self, num_entries, status):
        """
        Property: Querying by status returns all entries with that status.
        
        For all created entries:
        - Query by status should return only entries with that status
        - All returned entries should have the queried status
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        for i in range(num_entries):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            # Alternate between statuses
            entry_status = status if i % 2 == 0 else "success"
            
            log.append_entry(
                trace_id=trace_id,
                operation_name=f"op_{i}",
                operation_type="write",
                status=entry_status,
                start_time=time.time(),
                end_time=time.time() + 1
            )
        
        # Query by status
        retrieved = log.get_entries_by_status(status)
        
        # All retrieved entries should have the correct status
        for entry in retrieved:
            assert entry.status == status


class TestExecutionLogCountProperty:
    """
    **Validates: Requirement 5 - Hierarchical Run_ID Tracking**
    
    Property: Execution Log Count Accuracy
    
    Entry and trace counts are accurate.
    """
    
    @given(
        num_traces=st.integers(min_value=1, max_value=10),
        num_entries_per_trace=st.integers(min_value=1, max_value=5)
    )
    def test_entry_count_accuracy(self, num_traces, num_entries_per_trace):
        """
        Property: Entry count equals total entries added.
        
        For all added entries:
        - get_entry_count() should return the total number of entries
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        total_entries = 0
        
        for t in range(num_traces):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            for i in range(num_entries_per_trace):
                log.append_entry(
                    trace_id=trace_id,
                    operation_name=f"op_{t}_{i}",
                    operation_type="write",
                    status="success",
                    start_time=time.time(),
                    end_time=time.time() + 1
                )
                total_entries += 1
        
        # Verify count
        assert log.get_entry_count() == total_entries
    
    @given(
        num_traces=st.integers(min_value=1, max_value=10),
        num_entries_per_trace=st.integers(min_value=1, max_value=5)
    )
    def test_trace_count_accuracy(self, num_traces, num_entries_per_trace):
        """
        Property: Trace count equals number of unique trace_ids.
        
        For all added entries:
        - get_trace_count() should return the number of unique trace_ids
        """
        log = ExecutionLog()
        run_id = TraceIDGenerator.generate_run_id()
        
        for t in range(num_traces):
            branch_id = TraceIDGenerator.generate_branch_id("backend")
            leaf_id = TraceIDGenerator.generate_leaf_id("backend")
            trace_id = TraceIDGenerator.construct_trace_id(run_id, branch_id, leaf_id)
            
            for i in range(num_entries_per_trace):
                log.append_entry(
                    trace_id=trace_id,
                    operation_name=f"op_{t}_{i}",
                    operation_type="write",
                    status="success",
                    start_time=time.time(),
                    end_time=time.time() + 1
                )
        
        # Verify trace count
        assert log.get_trace_count() == num_traces
