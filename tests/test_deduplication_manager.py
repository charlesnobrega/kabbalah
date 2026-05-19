"""
Unit tests for the DeduplicationManager.

Tests cover:
- Error comparison with configurable matching criteria
- Occurrence counter increment for duplicates
- Deduplication query interface (find_duplicates, get_deduplication_stats)
- Configurable deduplication rules
- Error grouping and duplicate tracking
- Time window expiration

Requirements: 1.6, 11.6
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch

from src.kabbalah.deduplication_manager import (
    DeduplicationManager,
    DeduplicationRule,
    DeduplicationStats,
    DuplicateGroup,
)
from src.kabbalah.self_healing_models import ErrorReport, ErrorSeverity


class TestDeduplicationManagerInitialization:
    """Test DeduplicationManager initialization."""

    def test_initialization_with_defaults(self):
        """Test manager initializes with default settings."""
        manager = DeduplicationManager()
        assert manager.deduplication_window_seconds == 60
        assert manager.deduplication_rule is not None
        assert manager.error_groups == {}
        assert manager.error_history == []

    def test_initialization_with_custom_window(self):
        """Test manager initializes with custom window."""
        manager = DeduplicationManager(deduplication_window_seconds=120)
        assert manager.deduplication_window_seconds == 120

    def test_initialization_with_custom_rule(self):
        """Test manager initializes with custom rule."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=False,
            match_component=True,
        )
        manager = DeduplicationManager(deduplication_rule=rule)
        assert manager.deduplication_rule == rule


class TestDeduplicationRule:
    """Test DeduplicationRule configuration."""

    def test_default_rule(self):
        """Test default deduplication rule."""
        rule = DeduplicationRule()
        assert rule.match_error_type is True
        assert rule.match_message is True
        assert rule.match_component is True
        assert rule.match_file_path is False
        assert rule.match_line_number is False
        assert rule.use_fuzzy_matching is False

    def test_custom_rule(self):
        """Test custom deduplication rule."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=False,
            match_file_path=True,
        )
        assert rule.match_error_type is True
        assert rule.match_message is True
        assert rule.match_component is False
        assert rule.match_file_path is True


class TestErrorComparison:
    """Test error comparison functionality."""

    def test_compare_identical_errors(self):
        """Test comparing identical errors."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is True

    def test_compare_different_error_types(self):
        """Test comparing errors with different types."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="RuntimeError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is False

    def test_compare_different_messages(self):
        """Test comparing errors with different messages."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is False

    def test_compare_different_components(self):
        """Test comparing errors from different components."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is False

    def test_compare_with_custom_rule_ignore_component(self):
        """Test comparison with custom rule ignoring component."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=False,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is True

    def test_compare_with_file_path_matching(self):
        """Test comparison with file path matching enabled."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=True,
            match_file_path=True,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="file1.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="file2.py",
            line_number=10,
        )

        assert manager.compare_errors(error1, error2) is False

    def test_compare_with_line_number_matching(self):
        """Test comparison with line number matching enabled."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=True,
            match_line_number=True,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=20,
        )

        assert manager.compare_errors(error1, error2) is False


class TestMessageSimilarity:
    """Test message similarity calculation."""

    def test_identical_messages(self):
        """Test similarity of identical messages."""
        manager = DeduplicationManager()
        similarity = manager._calculate_message_similarity(
            "Test error message",
            "Test error message",
        )
        assert similarity == 1.0

    def test_completely_different_messages(self):
        """Test similarity of completely different messages."""
        manager = DeduplicationManager()
        similarity = manager._calculate_message_similarity(
            "abc",
            "xyz",
        )
        assert similarity < 0.5

    def test_similar_messages(self):
        """Test similarity of similar messages."""
        manager = DeduplicationManager()
        similarity = manager._calculate_message_similarity(
            "Test error message",
            "Test error message with extra",
        )
        assert 0.5 < similarity < 1.0

    def test_empty_messages(self):
        """Test similarity with empty messages."""
        manager = DeduplicationManager()
        similarity = manager._calculate_message_similarity("", "")
        assert similarity == 1.0

    def test_one_empty_message(self):
        """Test similarity with one empty message."""
        manager = DeduplicationManager()
        similarity = manager._calculate_message_similarity("", "Test")
        assert similarity == 0.0


class TestFuzzyMatching:
    """Test fuzzy message matching."""

    def test_fuzzy_matching_enabled(self):
        """Test fuzzy matching with similar messages."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=True,
            use_fuzzy_matching=True,
            message_similarity_threshold=0.7,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Connection timeout after 30 seconds",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Connection timeout after 31 seconds",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        # Should match with fuzzy matching
        assert manager.compare_errors(error1, error2) is True

    def test_fuzzy_matching_below_threshold(self):
        """Test fuzzy matching below threshold."""
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=True,
            match_component=True,
            use_fuzzy_matching=True,
            message_similarity_threshold=0.9,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        # Should not match (below threshold)
        assert manager.compare_errors(error1, error2) is False


class TestErrorProcessing:
    """Test error processing and deduplication."""

    def test_process_new_error(self):
        """Test processing a new error."""
        manager = DeduplicationManager()

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        is_duplicate, result = manager.process_error(error)

        assert is_duplicate is False
        assert result == error
        assert len(manager.error_groups) == 1
        assert len(manager.error_history) == 1

    def test_process_duplicate_error(self):
        """Test processing a duplicate error."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        is_dup1, result1 = manager.process_error(error1)
        is_dup2, result2 = manager.process_error(error2)

        assert is_dup1 is False
        assert is_dup2 is True
        assert result1 == error1
        assert result2 == error1  # Returns original error
        assert len(manager.error_groups) == 1
        assert len(manager.error_history) == 2
        assert error1.occurrence_count == 2

    def test_process_error_increments_occurrence_count(self):
        """Test that occurrence counter is incremented."""
        manager = DeduplicationManager()

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        # Process same error 5 times
        for i in range(5):
            manager.process_error(error)

        assert error.occurrence_count == 5

    def test_process_error_outside_window(self):
        """Test processing error outside deduplication window."""
        manager = DeduplicationManager(deduplication_window_seconds=1)

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        is_dup1, _ = manager.process_error(error1)
        assert is_dup1 is False
        assert len(manager.error_groups) == 1

        # Wait for window to expire
        time.sleep(1.1)

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        # Clear expired groups before processing new error
        manager.clear_expired_groups()

        is_dup2, _ = manager.process_error(error2)
        assert is_dup2 is False
        assert len(manager.error_groups) == 1  # New group replaces expired one


class TestFindDuplicates:
    """Test finding duplicate errors."""

    def test_find_duplicates_basic(self):
        """Test finding duplicates for an error."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error3 = ErrorReport(
            error_id="err-003",
            error_type="ValueError",
            message="Different error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)
        manager.process_error(error3)

        duplicates = manager.find_duplicates(error1)
        assert len(duplicates) == 1
        assert duplicates[0].error_id == "err-002"

    def test_find_duplicates_empty(self):
        """Test finding duplicates when none exist."""
        manager = DeduplicationManager()

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error)

        duplicates = manager.find_duplicates(error)
        assert len(duplicates) == 0


class TestDeduplicationStats:
    """Test deduplication statistics."""

    def test_get_deduplication_stats_empty(self):
        """Test statistics for empty manager."""
        manager = DeduplicationManager()

        stats = manager.get_deduplication_stats()

        assert stats.total_errors_detected == 0
        assert stats.total_duplicates_found == 0
        assert stats.total_occurrences == 0
        assert stats.errors_by_type == {}
        assert stats.errors_by_component == {}

    def test_get_deduplication_stats_with_errors(self):
        """Test statistics with errors."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        stats = manager.get_deduplication_stats()

        assert stats.total_errors_detected == 1
        assert stats.total_duplicates_found == 1
        assert stats.total_occurrences == 2
        assert stats.errors_by_type["ValueError"] == 1
        assert stats.errors_by_component["Leaf_Node"] == 1

    def test_get_deduplication_stats_multiple_types(self):
        """Test statistics with multiple error types."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="RuntimeError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        stats = manager.get_deduplication_stats()

        assert stats.total_errors_detected == 2
        assert stats.errors_by_type["ValueError"] == 1
        assert stats.errors_by_type["RuntimeError"] == 1


class TestConfigurableRules:
    """Test configurable deduplication rules."""

    def test_set_deduplication_rule(self):
        """Test setting deduplication rule."""
        manager = DeduplicationManager()

        new_rule = DeduplicationRule(
            match_error_type=True,
            match_message=False,
            match_component=True,
        )

        manager.set_deduplication_rule(new_rule)

        assert manager.deduplication_rule == new_rule

    def test_set_deduplication_window(self):
        """Test setting deduplication window."""
        manager = DeduplicationManager()

        manager.set_deduplication_window(120)

        assert manager.deduplication_window_seconds == 120

    def test_set_deduplication_window_invalid(self):
        """Test setting invalid deduplication window."""
        manager = DeduplicationManager()

        with pytest.raises(ValueError):
            manager.set_deduplication_window(0)

        with pytest.raises(ValueError):
            manager.set_deduplication_window(-1)


class TestDuplicateGroups:
    """Test duplicate group management."""

    def test_get_all_duplicate_groups(self):
        """Test getting all duplicate groups."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="RuntimeError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        groups = manager.get_all_duplicate_groups()

        assert len(groups) == 2

    def test_get_duplicate_groups_by_component(self):
        """Test getting duplicate groups by component."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        groups = manager.get_duplicate_groups_by_component("Leaf_Node")

        assert len(groups) == 1
        assert groups[0].original_error.component == "Leaf_Node"

    def test_get_duplicate_groups_by_error_type(self):
        """Test getting duplicate groups by error type."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="RuntimeError",
            message="Error 2",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        groups = manager.get_duplicate_groups_by_error_type("ValueError")

        assert len(groups) == 1
        assert groups[0].original_error.error_type == "ValueError"

    def test_get_duplicate_groups_by_severity(self):
        """Test getting duplicate groups by severity."""
        manager = DeduplicationManager()

        error1 = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Error 1",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        error2 = ErrorReport(
            error_id="err-002",
            error_type="ValueError",
            message="Error 2",
            severity=ErrorSeverity.CRITICAL,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error1)
        manager.process_error(error2)

        groups = manager.get_duplicate_groups_by_severity(ErrorSeverity.CRITICAL)

        assert len(groups) == 1
        assert groups[0].original_error.severity == ErrorSeverity.CRITICAL


class TestClearExpiredGroups:
    """Test clearing expired error groups."""

    def test_clear_expired_groups(self):
        """Test clearing expired groups."""
        manager = DeduplicationManager(deduplication_window_seconds=1)

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error)
        assert len(manager.error_groups) == 1

        # Wait for window to expire
        time.sleep(1.1)

        cleared = manager.clear_expired_groups()

        assert cleared == 1
        assert len(manager.error_groups) == 0


class TestClearAll:
    """Test clearing all data."""

    def test_clear_all(self):
        """Test clearing all data."""
        manager = DeduplicationManager()

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            timestamp=datetime.now(),
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=10,
        )

        manager.process_error(error)
        assert len(manager.error_groups) == 1
        assert len(manager.error_history) == 1

        manager.clear_all()

        assert len(manager.error_groups) == 0
        assert len(manager.error_history) == 0
