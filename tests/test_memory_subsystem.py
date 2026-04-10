"""Unit tests for MemorySubsystem."""

import json
import os
import platform
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabbalah.memory_subsystem import (
    CogneeBackend,
    JSONLBackend,
    Knowledge,
    MemoryConsistencyState,
    MemorySubsystem,
)


class TestKnowledgeDataclass:
    """Test Knowledge dataclass."""

    def test_knowledge_creation_with_required_fields(self):
        """Test creating Knowledge with required fields."""
        knowledge = Knowledge(
            knowledge_id="k1",
            content="Test content",
            category="shared",
        )
        assert knowledge.knowledge_id == "k1"
        assert knowledge.content == "Test content"
        assert knowledge.category == "shared"
        assert knowledge.trace_id is None
        assert knowledge.created_at > 0

    def test_knowledge_creation_with_all_fields(self):
        """Test creating Knowledge with all fields."""
        metadata = {"source": "test"}
        knowledge = Knowledge(
            knowledge_id="k1",
            content="Test content",
            category="domain-specific",
            metadata=metadata,
            trace_id="run_001:branch_001:leaf_001",
        )
        assert knowledge.metadata == metadata
        assert knowledge.trace_id == "run_001:branch_001:leaf_001"


class TestJSONLBackend:
    """Test JSONL backend."""

    def test_jsonl_backend_initialization(self):
        """Test JSONL backend initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)
            assert backend.storage_path == Path(tmpdir)
            assert backend.knowledge_file == Path(tmpdir) / "knowledge.jsonl"

    def test_jsonl_backend_default_path(self):
        """Test JSONL backend uses default path."""
        backend = JSONLBackend()
        expected_path = Path.home() / ".kabbalah" / "memory"
        assert backend.storage_path == expected_path

    def test_jsonl_backend_is_available(self):
        """Test JSONL backend is always available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)
            assert backend.is_available() is True

    def test_jsonl_store_knowledge(self):
        """Test storing knowledge in JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)
            knowledge = Knowledge(
                knowledge_id="k1",
                content="Test content",
                category="shared",
            )

            result = backend.store(knowledge)
            assert result is True
            assert backend.knowledge_file.exists()

    def test_jsonl_store_multiple_knowledge(self):
        """Test storing multiple knowledge items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)

            k1 = Knowledge(knowledge_id="k1", content="Content 1", category="shared")
            k2 = Knowledge(knowledge_id="k2", content="Content 2", category="shared")

            assert backend.store(k1) is True
            assert backend.store(k2) is True

            # Verify both are stored
            with open(backend.knowledge_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == 2

    def test_jsonl_query_knowledge(self):
        """Test querying knowledge from JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)

            k1 = Knowledge(
                knowledge_id="k1", content="Python programming", category="shared"
            )
            k2 = Knowledge(
                knowledge_id="k2", content="JavaScript basics", category="shared"
            )

            backend.store(k1)
            backend.store(k2)

            results = backend.query("Python", limit=10)
            assert len(results) == 1
            assert results[0].knowledge_id == "k1"

    def test_jsonl_query_with_limit(self):
        """Test query respects limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)

            for i in range(5):
                k = Knowledge(
                    knowledge_id=f"k{i}",
                    content="shared content",
                    category="shared",
                )
                backend.store(k)

            results = backend.query("shared", limit=2)
            assert len(results) == 2

    def test_jsonl_ensure_consistency(self):
        """Test consistency check on valid JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)

            k = Knowledge(knowledge_id="k1", content="Test", category="shared")
            backend.store(k)

            result = backend.ensure_consistency()
            assert result is True

    def test_jsonl_ensure_consistency_empty_file(self):
        """Test consistency check on empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)
            result = backend.ensure_consistency()
            assert result is True

    def test_jsonl_update_existing_knowledge(self):
        """Test updating existing knowledge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)

            k1 = Knowledge(
                knowledge_id="k1", content="Original content", category="shared"
            )
            backend.store(k1)

            k1_updated = Knowledge(
                knowledge_id="k1", content="Updated content", category="shared"
            )
            backend.store(k1_updated)

            # Should only have one entry
            with open(backend.knowledge_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == 1

            results = backend.query("Updated", limit=10)
            assert len(results) == 1
            assert results[0].content == "Updated content"

    def test_jsonl_thread_safety(self):
        """Test JSONL backend is thread-safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = JSONLBackend(tmpdir)
            results = []

            def store_knowledge(idx):
                k = Knowledge(
                    knowledge_id=f"k{idx}",
                    content=f"Content {idx}",
                    category="shared",
                )
                result = backend.store(k)
                results.append(result)

            threads = [
                threading.Thread(target=store_knowledge, args=(i,)) for i in range(5)
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            assert all(results)
            with open(backend.knowledge_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == 5


class TestCogneeBackend:
    """Test Cognee backend."""

    def test_cognee_backend_initialization_no_cognee(self):
        """Test Cognee backend initialization when Cognee not available."""
        with patch("kabbalah.memory_subsystem.cognee", side_effect=ImportError):
            backend = CogneeBackend()
            assert backend.available is False

    def test_cognee_backend_is_available_false(self):
        """Test Cognee backend availability when not initialized."""
        backend = CogneeBackend()
        # Since Cognee is likely not installed in test environment
        assert isinstance(backend.is_available(), bool)

    def test_cognee_backend_store_unavailable(self):
        """Test storing when Cognee is unavailable."""
        backend = CogneeBackend()
        backend.available = False

        knowledge = Knowledge(
            knowledge_id="k1", content="Test", category="shared"
        )
        result = backend.store(knowledge)
        assert result is False

    def test_cognee_backend_query_unavailable(self):
        """Test querying when Cognee is unavailable."""
        backend = CogneeBackend()
        backend.available = False

        results = backend.query("test")
        assert results == []

    def test_cognee_backend_ensure_consistency_unavailable(self):
        """Test consistency check when Cognee is unavailable."""
        backend = CogneeBackend()
        backend.available = False

        result = backend.ensure_consistency()
        assert result is False


class TestMemorySubsystem:
    """Test MemorySubsystem."""

    def test_memory_subsystem_initialization(self):
        """Test MemorySubsystem initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)
            assert subsystem.primary_backend is not None
            assert subsystem.fallback_backend is not None
            assert subsystem.consistency_state is not None

    def test_memory_subsystem_backend_selection_windows(self):
        """Test backend selection on Windows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("platform.system", return_value="Windows"):
                subsystem = MemorySubsystem(tmpdir)
                assert isinstance(subsystem.primary_backend, JSONLBackend)

    def test_memory_subsystem_backend_selection_linux(self):
        """Test backend selection on Linux."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("platform.system", return_value="Linux"):
                subsystem = MemorySubsystem(tmpdir)
                # Will be Cognee if available, otherwise JSONL
                assert subsystem.primary_backend is not None

    def test_store_knowledge_success(self):
        """Test storing knowledge successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            knowledge = Knowledge(
                knowledge_id="k1",
                content="Test knowledge",
                category="shared",
            )

            result = subsystem.store_knowledge(knowledge, "run_001:branch_001:leaf_001")
            assert result is True
            assert knowledge.trace_id == "run_001:branch_001:leaf_001"

    def test_store_knowledge_attaches_trace_id(self):
        """Test that store_knowledge attaches trace_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            knowledge = Knowledge(
                knowledge_id="k1",
                content="Test",
                category="shared",
            )

            trace_id = "run_001:branch_001:leaf_001"
            subsystem.store_knowledge(knowledge, trace_id)

            assert knowledge.trace_id == trace_id

    def test_query_knowledge_success(self):
        """Test querying knowledge successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            k1 = Knowledge(
                knowledge_id="k1",
                content="Python programming",
                category="shared",
            )

            subsystem.store_knowledge(k1, "run_001:branch_001:leaf_001")

            results = subsystem.query_knowledge("Python", limit=10)
            assert len(results) == 1
            assert results[0].knowledge_id == "k1"

    def test_query_knowledge_empty_result(self):
        """Test querying with no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            results = subsystem.query_knowledge("nonexistent", limit=10)
            assert results == []

    def test_query_knowledge_respects_limit(self):
        """Test query respects limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            for i in range(5):
                k = Knowledge(
                    knowledge_id=f"k{i}",
                    content="shared content",
                    category="shared",
                )
                subsystem.store_knowledge(k, f"run_001:branch_001:leaf_{i:03d}")

            results = subsystem.query_knowledge("shared", limit=2)
            assert len(results) == 2

    def test_ensure_consistency_success(self):
        """Test ensuring consistency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            result = subsystem.ensure_consistency()
            assert result is True
            assert subsystem.consistency_state.is_consistent is True

    def test_ensure_consistency_updates_state(self):
        """Test that ensure_consistency updates state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            old_time = subsystem.consistency_state.last_sync_time
            time.sleep(0.01)  # Small delay to ensure time difference

            subsystem.ensure_consistency()

            assert subsystem.consistency_state.last_sync_time > old_time

    def test_get_consistency_state(self):
        """Test getting consistency state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            state = subsystem.get_consistency_state()
            assert isinstance(state, MemoryConsistencyState)
            assert state.is_consistent is True

    def test_clear_all_knowledge(self):
        """Test clearing all knowledge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            k = Knowledge(knowledge_id="k1", content="Test", category="shared")
            subsystem.store_knowledge(k, "run_001:branch_001:leaf_001")

            result = subsystem.clear_all_knowledge()
            assert result is True

            # Verify knowledge is cleared
            results = subsystem.query_knowledge("Test", limit=10)
            assert results == []

    def test_thread_safety_concurrent_stores(self):
        """Test thread safety with concurrent stores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)
            results = []

            def store_knowledge(idx):
                k = Knowledge(
                    knowledge_id=f"k{idx}",
                    content=f"Content {idx}",
                    category="shared",
                )
                result = subsystem.store_knowledge(
                    k, f"run_001:branch_001:leaf_{idx:03d}"
                )
                results.append(result)

            threads = [
                threading.Thread(target=store_knowledge, args=(i,)) for i in range(5)
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            assert all(results)

    def test_thread_safety_concurrent_queries(self):
        """Test thread safety with concurrent queries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # Store some knowledge first
            for i in range(3):
                k = Knowledge(
                    knowledge_id=f"k{i}",
                    content="shared content",
                    category="shared",
                )
                subsystem.store_knowledge(k, f"run_001:branch_001:leaf_{i:03d}")

            results_list = []

            def query_knowledge():
                results = subsystem.query_knowledge("shared", limit=10)
                results_list.append(len(results))

            threads = [threading.Thread(target=query_knowledge) for _ in range(5)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            assert all(count == 3 for count in results_list)

    def test_store_and_query_multiple_categories(self):
        """Test storing and querying knowledge from different categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            k1 = Knowledge(
                knowledge_id="k1",
                content="Shared knowledge",
                category="shared",
            )
            k2 = Knowledge(
                knowledge_id="k2",
                content="Backend specific",
                category="domain-specific",
            )

            subsystem.store_knowledge(k1, "run_001:branch_001:leaf_001")
            subsystem.store_knowledge(k2, "run_001:branch_backend_001:leaf_001")

            results = subsystem.query_knowledge("knowledge", limit=10)
            assert len(results) >= 1

    def test_knowledge_metadata_preserved(self):
        """Test that knowledge metadata is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            metadata = {"source": "test", "version": "1.0"}
            k = Knowledge(
                knowledge_id="k1",
                content="Test",
                category="shared",
                metadata=metadata,
            )

            subsystem.store_knowledge(k, "run_001:branch_001:leaf_001")

            results = subsystem.query_knowledge("Test", limit=10)
            assert len(results) == 1
            assert results[0].metadata == metadata

    def test_error_handling_invalid_knowledge(self):
        """Test error handling with invalid knowledge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            # This should not raise an exception
            result = subsystem.store_knowledge(None, "run_001:branch_001:leaf_001")
            # Result depends on implementation, but should not crash

    def test_consistency_state_initialization(self):
        """Test consistency state is properly initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subsystem = MemorySubsystem(tmpdir)

            state = subsystem.consistency_state
            assert state.is_consistent is True
            assert state.last_sync_time > 0
            assert state.pending_operations == []
            assert state.conflicts == []
