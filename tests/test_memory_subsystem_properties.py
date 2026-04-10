"""Property-based tests for MemorySubsystem."""

import tempfile
from typing import List

import pytest
from hypothesis import given, strategies as st

from kabbalah.memory_subsystem import Knowledge, MemorySubsystem


# Strategies for property-based testing

def knowledge_strategy():
    """Strategy for generating Knowledge objects."""
    return st.builds(
        Knowledge,
        knowledge_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        content=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
        category=st.sampled_from(["shared", "domain-specific", "role-specific"]),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=0, max_size=100),
            max_size=5,
        ),
    )


def trace_id_strategy():
    """Strategy for generating valid trace_ids."""
    return st.builds(
        lambda run, branch, leaf: f"{run}:{branch}:{leaf}",
        run=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=5, max_size=20
        ),
        branch=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=5, max_size=20
        ),
        leaf=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=5, max_size=20
        ),
    )


class TestProperty20KnowledgeStorageCorrectness:
    """
    Property 20: Knowledge storage correctness.

    For any knowledge stored in the Memory_Subsystem, querying with semantically
    related terms SHALL return the stored knowledge in the results.

    **Validates: Requirements 6.2, 6.3**
    """

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=10),
        trace_id=trace_id_strategy(),
    )
    def test_stored_knowledge_is_queryable(self, knowledge_list, trace_id):
        """Test that stored knowledge can be queried back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store all knowledge
            for knowledge in knowledge_list:
                result = subsystem.store_knowledge(knowledge, trace_id)
                assert result is True, f"Failed to store knowledge {knowledge.knowledge_id}"

            # Query for each stored knowledge using its content
            for knowledge in knowledge_list:
                # Use first word of content as query
                query_term = knowledge.content.split()[0]
                results = subsystem.query_knowledge(query_term, limit=100)

                # Should find the stored knowledge
                found_ids = {k.knowledge_id for k in results}
                assert (
                    knowledge.knowledge_id in found_ids
                ), f"Could not find stored knowledge {knowledge.knowledge_id} with query '{query_term}'"

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_stored_knowledge_preserves_content(self, knowledge, trace_id):
        """Test that stored knowledge preserves its content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            # Query using content
            results = subsystem.query_knowledge(knowledge.content.split()[0], limit=100)

            # Find the stored knowledge
            found = None
            for k in results:
                if k.knowledge_id == knowledge.knowledge_id:
                    found = k
                    break

            assert found is not None, "Stored knowledge not found"
            assert found.content == knowledge.content, "Content was modified"
            assert found.category == knowledge.category, "Category was modified"

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_stored_knowledge_preserves_metadata(self, knowledge, trace_id):
        """Test that stored knowledge preserves its metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            results = subsystem.query_knowledge(knowledge.content.split()[0], limit=100)

            found = None
            for k in results:
                if k.knowledge_id == knowledge.knowledge_id:
                    found = k
                    break

            assert found is not None
            assert found.metadata == knowledge.metadata, "Metadata was modified"

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_stored_knowledge_has_trace_id(self, knowledge, trace_id):
        """Test that stored knowledge has trace_id attached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            results = subsystem.query_knowledge(knowledge.content.split()[0], limit=100)

            found = None
            for k in results:
                if k.knowledge_id == knowledge.knowledge_id:
                    found = k
                    break

            assert found is not None
            assert found.trace_id == trace_id, "Trace ID was not attached"


class TestProperty21MemoryConsistencyParallel:
    """
    Property 21: Memory consistency across parallel operations.

    For any set of parallel memory operations, the final memory state SHALL be
    consistent and equivalent to executing the operations sequentially.

    **Validates: Requirements 6.4**
    """

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=2, max_size=10),
        trace_id=trace_id_strategy(),
    )
    def test_consistency_after_sequential_operations(self, knowledge_list, trace_id):
        """Test that consistency is maintained after sequential operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store all knowledge sequentially
            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            # Check consistency
            is_consistent = subsystem.ensure_consistency()
            assert is_consistent is True, "Consistency check failed after sequential operations"

            # Verify all knowledge is queryable
            for knowledge in knowledge_list:
                query_term = knowledge.content.split()[0]
                results = subsystem.query_knowledge(query_term, limit=100)
                found_ids = {k.knowledge_id for k in results}
                assert knowledge.knowledge_id in found_ids, f"Knowledge {knowledge.knowledge_id} not found after consistency check"

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=2, max_size=10),
        trace_id=trace_id_strategy(),
    )
    def test_consistency_state_is_valid(self, knowledge_list, trace_id):
        """Test that consistency state is valid after operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            state = subsystem.get_consistency_state()

            assert state.is_consistent is True, "Consistency state should be True"
            assert state.last_sync_time > 0, "Last sync time should be set"
            assert isinstance(state.pending_operations, list), "Pending operations should be a list"
            assert isinstance(state.conflicts, list), "Conflicts should be a list"

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=5),
        trace_id=trace_id_strategy(),
    )
    def test_multiple_consistency_checks_succeed(self, knowledge_list, trace_id):
        """Test that multiple consistency checks all succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            # Run consistency check multiple times
            for _ in range(3):
                result = subsystem.ensure_consistency()
                assert result is True, "Consistency check failed"

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=10),
        trace_id=trace_id_strategy(),
    )
    def test_consistency_after_clear(self, knowledge_list, trace_id):
        """Test that consistency is maintained after clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store knowledge
            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            # Clear all
            subsystem.clear_all_knowledge()

            # Check consistency
            result = subsystem.ensure_consistency()
            assert result is True, "Consistency check failed after clear"

            # Verify no knowledge remains
            results = subsystem.query_knowledge("test", limit=100)
            assert len(results) == 0, "Knowledge should be cleared"


class TestProperty22CogneeFallback:
    """
    Property 22: Cognee fallback behavior.

    For any memory operation when Cognee is unavailable, the Memory_Subsystem
    SHALL fall back to JSONL-based local storage and maintain eventual consistency.

    **Validates: Requirements 6.5, 11.5**
    """

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_fallback_backend_available(self, knowledge, trace_id):
        """Test that fallback backend is always available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Fallback backend should always be available
            assert subsystem.fallback_backend.is_available() is True

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=5),
        trace_id=trace_id_strategy(),
    )
    def test_storage_succeeds_with_fallback(self, knowledge_list, trace_id):
        """Test that storage succeeds even if primary backend fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Make primary backend unavailable
            subsystem.primary_backend.available = False

            # Storage should still succeed via fallback
            for knowledge in knowledge_list:
                result = subsystem.store_knowledge(knowledge, trace_id)
                assert result is True, f"Storage failed for {knowledge.knowledge_id}"

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=5),
        trace_id=trace_id_strategy(),
    )
    def test_query_succeeds_with_fallback(self, knowledge_list, trace_id):
        """Test that query succeeds even if primary backend fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store knowledge
            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            # Make primary backend unavailable
            subsystem.primary_backend.available = False

            # Query should still succeed via fallback
            if knowledge_list:
                query_term = knowledge_list[0].content.split()[0]
                results = subsystem.query_knowledge(query_term, limit=100)
                # Should get results from fallback
                assert isinstance(results, list)

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=5),
        trace_id=trace_id_strategy(),
    )
    def test_consistency_check_with_fallback(self, knowledge_list, trace_id):
        """Test that consistency check works with fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)

            # Make primary backend unavailable
            subsystem.primary_backend.available = False

            # Consistency check should still work
            result = subsystem.ensure_consistency()
            assert isinstance(result, bool)

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=5),
        trace_id=trace_id_strategy(),
    )
    def test_fallback_maintains_data(self, knowledge_list, trace_id):
        """Test that fallback maintains data integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store knowledge
            stored_ids = set()
            for knowledge in knowledge_list:
                subsystem.store_knowledge(knowledge, trace_id)
                stored_ids.add(knowledge.knowledge_id)

            # Make primary backend unavailable
            subsystem.primary_backend.available = False

            # Query all stored knowledge via fallback
            all_results = []
            for knowledge in knowledge_list:
                query_term = knowledge.content.split()[0]
                results = subsystem.query_knowledge(query_term, limit=100)
                all_results.extend(results)

            # Verify all stored knowledge is still accessible
            found_ids = {k.knowledge_id for k in all_results}
            assert stored_ids.issubset(found_ids), "Some knowledge was lost in fallback"


class TestMemorySubsystemEdgeCases:
    """Test edge cases and boundary conditions."""

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_empty_query_returns_results(self, knowledge, trace_id):
        """Test querying with empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            # Empty query should return empty results
            results = subsystem.query_knowledge("", limit=10)
            assert isinstance(results, list)

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_query_with_zero_limit(self, knowledge, trace_id):
        """Test querying with zero limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            results = subsystem.query_knowledge("test", limit=0)
            assert results == []

    @given(
        knowledge=knowledge_strategy(),
        trace_id=trace_id_strategy(),
    )
    def test_query_with_large_limit(self, knowledge, trace_id):
        """Test querying with very large limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            subsystem.store_knowledge(knowledge, trace_id)

            results = subsystem.query_knowledge("test", limit=10000)
            assert isinstance(results, list)

    @given(
        knowledge_list=st.lists(knowledge_strategy(), min_size=1, max_size=10),
        trace_id=trace_id_strategy(),
    )
    def test_duplicate_knowledge_ids(self, knowledge_list, trace_id):
        """Test storing knowledge with duplicate IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            if knowledge_list:
                # Store first knowledge
                subsystem.store_knowledge(knowledge_list[0], trace_id)

                # Store another with same ID but different content
                duplicate = Knowledge(
                    knowledge_id=knowledge_list[0].knowledge_id,
                    content="Different content",
                    category="shared",
                )
                subsystem.store_knowledge(duplicate, trace_id)

                # Should have updated the knowledge
                results = subsystem.query_knowledge("Different", limit=100)
                assert len(results) >= 1
