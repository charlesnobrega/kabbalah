"""
Property-based tests for the DeduplicationManager.

Tests verify universal properties that should hold across all valid inputs:
- Error deduplication within time window
- Occurrence counter increment
- Error comparison consistency
- Deduplication statistics accuracy

Requirements: 1.6, 11.6
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest

from src.kabbalah.deduplication_manager import (
    DeduplicationManager,
    DeduplicationRule,
)
from src.kabbalah.self_healing_models import ErrorReport, ErrorSeverity


# Strategies for generating test data
@st.composite
def error_reports(draw):
    """Generate random ErrorReport objects."""
    error_types = ["ValueError", "RuntimeError", "TypeError", "KeyError"]
    components = ["Leaf_Node", "Domain_Orchestrator", "Root_Orchestrator"]
    severities = [
        ErrorSeverity.CRITICAL,
        ErrorSeverity.HIGH,
        ErrorSeverity.MEDIUM,
        ErrorSeverity.LOW,
    ]

    return ErrorReport(
        error_id=draw(st.text(min_size=1, max_size=20)),
        error_type=draw(st.sampled_from(error_types)),
        message=draw(st.text(min_size=1, max_size=100)),
        severity=draw(st.sampled_from(severities)),
        timestamp=datetime.now(),
        component=draw(st.sampled_from(components)),
        context={},
        stack_trace="",
        file_path="test.py",
        line_number=draw(st.integers(min_value=1, max_value=1000)),
    )


class TestDeduplicationProperties:
    """Property-based tests for deduplication."""

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_identical_errors_deduplicated(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any two identical errors detected within a 60-second window,
        the system SHALL create only one ErrorReport and increment the occurrence_count
        rather than creating duplicate reports.
        """
        manager = DeduplicationManager(deduplication_window_seconds=60)

        if len(errors) < 2:
            pytest.skip("Need at least 2 errors")

        # Use first error as base
        base_error = errors[0]

        # Create identical error
        identical_error = ErrorReport(
            error_id="err-dup",
            error_type=base_error.error_type,
            message=base_error.message,
            severity=base_error.severity,
            timestamp=datetime.now(),
            component=base_error.component,
            context={},
            stack_trace="",
            file_path=base_error.file_path,
            line_number=base_error.line_number,
        )

        # Process both errors
        is_dup1, result1 = manager.process_error(base_error)
        is_dup2, result2 = manager.process_error(identical_error)

        # First should not be duplicate
        assert is_dup1 is False
        # Second should be duplicate
        assert is_dup2 is True
        # Should return original error
        assert result2 == base_error
        # Occurrence count should be incremented
        assert base_error.occurrence_count == 2
        # Only one group should exist
        assert len(manager.error_groups) == 1

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_different_errors_not_deduplicated(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any two different errors (different type, message, or component),
        the system SHALL NOT deduplicate them and SHALL create separate ErrorReports.
        """
        manager = DeduplicationManager()

        if len(errors) < 2:
            pytest.skip("Need at least 2 errors")

        # Process first two errors
        is_dup1, _ = manager.process_error(errors[0])
        is_dup2, _ = manager.process_error(errors[1])

        # Check if errors are actually different
        are_different = (
            errors[0].error_type != errors[1].error_type
            or errors[0].message != errors[1].message
            or errors[0].component != errors[1].component
        )

        if are_different:
            # Both should not be duplicates
            assert is_dup1 is False
            assert is_dup2 is False
            # Should have 2 groups
            assert len(manager.error_groups) == 2

    @given(st.lists(error_reports(), min_size=1, max_size=50))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_occurrence_count_increments_correctly(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any set of identical errors, the occurrence_count SHALL
        be incremented correctly for each duplicate detected.
        """
        manager = DeduplicationManager()

        if len(errors) < 1:
            pytest.skip("Need at least 1 error")

        base_error = errors[0]

        # Process the base error first
        is_dup, original = manager.process_error(base_error)
        assert is_dup is False

        # Create multiple identical errors
        for i in range(5):
            identical_error = ErrorReport(
                error_id=f"err-{i}",
                error_type=base_error.error_type,
                message=base_error.message,
                severity=base_error.severity,
                timestamp=datetime.now(),
                component=base_error.component,
                context={},
                stack_trace="",
                file_path=base_error.file_path,
                line_number=base_error.line_number,
            )
            manager.process_error(identical_error)

        # Occurrence count should be 1 + 5 = 6
        assert original.occurrence_count == 6

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_deduplication_stats_accuracy(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any set of errors, the deduplication statistics SHALL
        accurately reflect the total errors, duplicates, and occurrences.
        """
        manager = DeduplicationManager()

        # Process all errors
        for error in errors:
            manager.process_error(error)

        stats = manager.get_deduplication_stats()

        # Total occurrences should equal sum of all occurrence counts
        total_occurrences = sum(
            group.occurrence_count
            for group in manager.error_groups.values()
        )
        assert stats.total_occurrences == total_occurrences

        # Total errors detected should equal number of groups
        assert stats.total_errors_detected == len(manager.error_groups)

        # Total duplicates should equal sum of duplicate counts
        total_duplicates = sum(
            group.duplicate_count
            for group in manager.error_groups.values()
        )
        assert stats.total_duplicates_found == total_duplicates

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_error_comparison_consistency(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any two errors, the comparison result SHALL be consistent
        and symmetric (if A == B then B == A).
        """
        manager = DeduplicationManager()

        if len(errors) < 2:
            pytest.skip("Need at least 2 errors")

        error1 = errors[0]
        error2 = errors[1]

        # Compare both directions
        result1 = manager.compare_errors(error1, error2)
        result2 = manager.compare_errors(error2, error1)

        # Results should be symmetric
        assert result1 == result2

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_error_comparison_reflexive(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any error, comparing it with itself SHALL always return True.
        """
        manager = DeduplicationManager()

        if len(errors) < 1:
            pytest.skip("Need at least 1 error")

        error = errors[0]

        # Compare with itself
        result = manager.compare_errors(error, error)

        # Should always be True
        assert result is True

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_find_duplicates_returns_only_duplicates(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any error, find_duplicates SHALL return only errors that
        match the given error according to the deduplication rule.
        """
        manager = DeduplicationManager()

        if len(errors) < 2:
            pytest.skip("Need at least 2 errors")

        base_error = errors[0]

        # Process all errors
        for error in errors:
            manager.process_error(error)

        # Find duplicates
        duplicates = manager.find_duplicates(base_error)

        # All duplicates should match the base error
        for duplicate in duplicates:
            assert manager.compare_errors(base_error, duplicate)

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_deduplication_rule_application(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any deduplication rule, the comparison SHALL respect
        the rule's matching criteria.
        """
        # Create rule that only matches error type
        rule = DeduplicationRule(
            match_error_type=True,
            match_message=False,
            match_component=False,
        )
        manager = DeduplicationManager(deduplication_rule=rule)

        if len(errors) < 2:
            pytest.skip("Need at least 2 errors")

        error1 = errors[0]
        error2 = ErrorReport(
            error_id="err-different",
            error_type=error1.error_type,  # Same type
            message="Different message",  # Different message
            severity=error1.severity,
            timestamp=datetime.now(),
            component="Different_Component",  # Different component
            context={},
            stack_trace="",
            file_path="different.py",
            line_number=999,
        )

        # Should match because only error_type is checked
        result = manager.compare_errors(error1, error2)
        assert result is True

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_error_history_contains_all_processed_errors(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any set of processed errors, the error_history SHALL
        contain all processed errors (both originals and duplicates).
        """
        manager = DeduplicationManager()

        # Process all errors
        for error in errors:
            manager.process_error(error)

        # Error history should contain all processed errors
        assert len(manager.error_history) == len(errors)

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_clear_all_removes_all_data(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: After calling clear_all(), the manager SHALL have no
        error groups or history.
        """
        manager = DeduplicationManager()

        # Process all errors
        for error in errors:
            manager.process_error(error)

        # Clear all
        manager.clear_all()

        # Should be empty
        assert len(manager.error_groups) == 0
        assert len(manager.error_history) == 0

    @given(st.lists(error_reports(), min_size=1, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_duplicate_group_tracking(self, errors):
        """
        **Validates: Requirements 1.6**

        Property: For any error group, the duplicate_count and occurrence_count
        SHALL be consistent (occurrence_count = 1 + duplicate_count).
        """
        manager = DeduplicationManager()

        if len(errors) < 1:
            pytest.skip("Need at least 1 error")

        base_error = errors[0]

        # Create multiple identical errors
        for i in range(10):
            identical_error = ErrorReport(
                error_id=f"err-{i}",
                error_type=base_error.error_type,
                message=base_error.message,
                severity=base_error.severity,
                timestamp=datetime.now(),
                component=base_error.component,
                context={},
                stack_trace="",
                file_path=base_error.file_path,
                line_number=base_error.line_number,
            )
            manager.process_error(identical_error)

        # Get the group
        groups = manager.get_all_duplicate_groups()
        assert len(groups) == 1

        group = groups[0]

        # Check consistency
        assert group.occurrence_count == 1 + group.duplicate_count
        assert group.occurrence_count == 10
        assert group.duplicate_count == 9
