"""
Unit tests for the ErrorDetectionModule.

Tests cover:
- Exception capture with full context
- Test failure capture with assertion details
- Severity classification based on component type
- Error deduplication within time window
- Error history storage and querying
- Error statistics

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3, 11.4
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from kabbalah.error_detection_module import ErrorDetectionModule
from kabbalah.self_healing_models import ErrorSeverity


class TestErrorDetectionModuleInitialization:
    """Test ErrorDetectionModule initialization."""

    def test_initialization_with_default_window(self):
        """Test module initializes with default deduplication window."""
        module = ErrorDetectionModule()
        assert module.deduplication_window_seconds == 60
        assert module.error_history == []
        assert "Intake_Node" in module.critical_components
        assert "Root_Orchestrator" in module.critical_components
        assert "Synthesizer" in module.critical_components

    def test_initialization_with_custom_window(self):
        """Test module initializes with custom deduplication window."""
        module = ErrorDetectionModule(deduplication_window_seconds=120)
        assert module.deduplication_window_seconds == 120


class TestExceptionCapture:
    """Test exception capture functionality."""

    def test_capture_exception_basic(self):
        """Test capturing a basic exception."""
        module = ErrorDetectionModule()
        exception = ValueError("Test error message")

        error_report = module.capture_exception(
            exception=exception,
            component="Leaf_Node",
            context={"trace_id": "trace-123"},
        )

        assert error_report is not None
        assert error_report.error_type == "ValueError"
        assert error_report.message == "Test error message"
        assert error_report.component == "Leaf_Node"
        assert error_report.severity == ErrorSeverity.MEDIUM
        assert error_report.context["trace_id"] == "trace-123"
        assert error_report.occurrence_count == 1
        assert error_report.status == "DETECTED"
        assert len(module.error_history) == 1

    def test_capture_exception_with_critical_component(self):
        """Test exception in critical component is marked CRITICAL."""
        module = ErrorDetectionModule()
        exception = RuntimeError("Critical error")

        error_report = module.capture_exception(
            exception=exception,
            component="Root_Orchestrator",
        )

        assert error_report.severity == ErrorSeverity.CRITICAL

    def test_capture_exception_with_high_impact_component(self):
        """Test exception in high-impact component is marked HIGH."""
        module = ErrorDetectionModule()
        exception = RuntimeError("High impact error")

        error_report = module.capture_exception(
            exception=exception,
            component="Domain_Orchestrator",
        )

        assert error_report.severity == ErrorSeverity.HIGH

    def test_capture_exception_with_no_context(self):
        """Test capturing exception with no context provided."""
        module = ErrorDetectionModule()
        exception = ValueError("Test error")

        error_report = module.capture_exception(
            exception=exception,
            component="Leaf_Node",
        )

        assert error_report is not None
        assert error_report.context == {}

    def test_capture_exception_generates_unique_error_id(self):
        """Test that each exception gets a unique error_id."""
        module = ErrorDetectionModule()
        exception1 = ValueError("Error 1")
        exception2 = ValueError("Error 2")

        report1 = module.capture_exception(exception1, "Leaf_Node")
        report2 = module.capture_exception(exception2, "Leaf_Node")

        assert report1.error_id != report2.error_id
        assert report1.error_id.startswith("err-")
        assert report2.error_id.startswith("err-")

    def test_capture_exception_extracts_file_and_line(self):
        """Test that exception capture extracts file path and line number."""
        module = ErrorDetectionModule()

        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_report = module.capture_exception(e, "Leaf_Node")

        assert error_report.file_path.endswith(".py")
        assert error_report.line_number > 0

    def test_capture_exception_adds_to_history(self):
        """Test that captured exceptions are added to error history."""
        module = ErrorDetectionModule()
        exception1 = ValueError("Error 1")
        exception2 = RuntimeError("Error 2")

        module.capture_exception(exception1, "Leaf_Node")
        module.capture_exception(exception2, "Root_Orchestrator")

        assert len(module.error_history) == 2


class TestTestFailureCapture:
    """Test test failure capture functionality."""

    def test_capture_test_failure_basic(self):
        """Test capturing a basic test failure."""
        module = ErrorDetectionModule()

        error_report = module.capture_test_failure(
            test_name="test_example",
            failure_message="AssertionError: expected 5 but got 3",
            assertion_details={"expected": 5, "actual": 3},
            test_context={"module": "test_module", "class": "TestClass"},
        )

        assert error_report is not None
        assert error_report.error_type == "TestFailure"
        assert error_report.message == "AssertionError: expected 5 but got 3"
        assert error_report.component == "TestFramework"
        assert error_report.severity == ErrorSeverity.HIGH
        assert error_report.context["test_name"] == "test_example"
        assert error_report.context["assertion_details"]["expected"] == 5
        assert error_report.occurrence_count == 1

    def test_capture_test_failure_with_no_details(self):
        """Test capturing test failure with minimal details."""
        module = ErrorDetectionModule()

        error_report = module.capture_test_failure(
            test_name="test_simple",
            failure_message="Test failed",
        )

        assert error_report is not None
        assert error_report.error_type == "TestFailure"
        assert error_report.severity == ErrorSeverity.HIGH
        assert error_report.context["test_name"] == "test_simple"

    def test_capture_test_failure_adds_to_history(self):
        """Test that captured test failures are added to error history."""
        module = ErrorDetectionModule()

        module.capture_test_failure("test_1", "Failed")
        module.capture_test_failure("test_2", "Failed")

        assert len(module.error_history) == 2


class TestSeverityClassification:
    """Test error severity classification."""

    def test_classify_severity_critical_components(self):
        """Test CRITICAL severity for critical components."""
        module = ErrorDetectionModule()

        for component in ["Intake_Node", "Root_Orchestrator", "Synthesizer"]:
            severity = module.classify_severity(
                component=component,
                error_type="RuntimeError",
            )
            assert severity == ErrorSeverity.CRITICAL

    def test_classify_severity_high_impact_components(self):
        """Test HIGH severity for high-impact components."""
        module = ErrorDetectionModule()

        for component in ["Domain_Orchestrator", "FSM_Enforcement"]:
            severity = module.classify_severity(
                component=component,
                error_type="RuntimeError",
            )
            assert severity == ErrorSeverity.HIGH

    def test_classify_severity_medium_impact_components(self):
        """Test MEDIUM severity for medium-impact components."""
        module = ErrorDetectionModule()

        severity = module.classify_severity(
            component="Leaf_Node",
            error_type="RuntimeError",
        )
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_severity_multi_component_impact(self):
        """Test HIGH severity for multi-component impact."""
        module = ErrorDetectionModule()

        severity = module.classify_severity(
            component="Leaf_Node",
            error_type="RuntimeError",
            affected_components=["Leaf_Node", "Domain_Orchestrator"],
        )
        assert severity == ErrorSeverity.HIGH

    def test_classify_severity_informational_errors(self):
        """Test INFO severity for informational error types."""
        module = ErrorDetectionModule()

        for error_type in ["DeprecationWarning", "UserWarning"]:
            severity = module.classify_severity(
                component="Leaf_Node",
                error_type=error_type,
            )
            assert severity == ErrorSeverity.INFO

    def test_classify_severity_unknown_component_defaults_to_medium(self):
        """Test unknown components default to MEDIUM severity."""
        module = ErrorDetectionModule()

        severity = module.classify_severity(
            component="UnknownComponent",
            error_type="RuntimeError",
        )
        assert severity == ErrorSeverity.MEDIUM


class TestErrorDeduplication:
    """Test error deduplication functionality."""

    def test_deduplicate_identical_error_within_window(self):
        """Test identical errors within window are deduplicated."""
        module = ErrorDetectionModule()
        exception = ValueError("Test error")

        # Capture same error twice
        report1 = module.capture_exception(exception, "Leaf_Node")
        report2 = module.capture_exception(exception, "Leaf_Node")

        # Second should be deduplicated
        assert report1 is not None
        assert report2 is None
        assert len(module.error_history) == 1
        assert module.error_history[0].occurrence_count == 2

    def test_deduplicate_different_errors_not_deduplicated(self):
        """Test different errors are not deduplicated."""
        module = ErrorDetectionModule()

        report1 = module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        report2 = module.capture_exception(ValueError("Error 2"), "Leaf_Node")

        assert report1 is not None
        assert report2 is not None
        assert len(module.error_history) == 2

    def test_deduplicate_same_error_different_component_not_deduplicated(self):
        """Test same error in different component is not deduplicated."""
        module = ErrorDetectionModule()
        exception = ValueError("Test error")

        report1 = module.capture_exception(exception, "Leaf_Node")
        report2 = module.capture_exception(exception, "Domain_Orchestrator")

        assert report1 is not None
        assert report2 is not None
        assert len(module.error_history) == 2

    def test_deduplicate_outside_time_window_not_deduplicated(self):
        """Test identical error outside time window is not deduplicated."""
        module = ErrorDetectionModule(deduplication_window_seconds=1)
        exception = ValueError("Test error")

        report1 = module.capture_exception(exception, "Leaf_Node")

        # Wait for window to expire
        import time
        time.sleep(1.1)

        report2 = module.capture_exception(exception, "Leaf_Node")

        assert report1 is not None
        assert report2 is not None
        assert len(module.error_history) == 2
        assert report1.error_id != report2.error_id

    def test_deduplicate_with_custom_window(self):
        """Test deduplication with custom window."""
        module = ErrorDetectionModule(deduplication_window_seconds=120)
        exception = ValueError("Test error")

        report1 = module.capture_exception(exception, "Leaf_Node")

        # Mock time to be within custom window
        with patch("kabbalah.error_detection_module.datetime") as mock_datetime:
            # Set current time to 60 seconds later
            mock_datetime.now.return_value = (
                report1.timestamp + timedelta(seconds=60)
            )
            report2 = module.capture_exception(exception, "Leaf_Node")

        # Should still be deduplicated (within 120s window)
        assert report2 is None
        assert module.error_history[0].occurrence_count == 2


class TestErrorHistoryQuerying:
    """Test error history querying functionality."""

    def test_query_error_history_all(self):
        """Test querying all errors in history."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(RuntimeError("Error 2"), "Root_Orchestrator")

        results = module.query_error_history()
        assert len(results) == 2

    def test_query_error_history_by_error_type(self):
        """Test querying errors by error type."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(RuntimeError("Error 2"), "Leaf_Node")

        results = module.query_error_history(error_type="ValueError")
        assert len(results) == 1
        assert results[0].error_type == "ValueError"

    def test_query_error_history_by_component(self):
        """Test querying errors by component."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Root_Orchestrator")

        results = module.query_error_history(component="Leaf_Node")
        assert len(results) == 1
        assert results[0].component == "Leaf_Node"

    def test_query_error_history_by_severity(self):
        """Test querying errors by severity."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Root_Orchestrator")

        results = module.query_error_history(severity=ErrorSeverity.CRITICAL)
        assert len(results) == 1
        assert results[0].severity == ErrorSeverity.CRITICAL

    def test_query_error_history_by_time_range(self):
        """Test querying errors by time range."""
        module = ErrorDetectionModule()

        now = datetime.now()
        report1 = module.capture_exception(ValueError("Error 1"), "Leaf_Node")

        # Mock time to be 2 seconds later
        with patch("kabbalah.error_detection_module.datetime") as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(seconds=2)
            report2 = module.capture_exception(ValueError("Error 2"), "Leaf_Node")

        # Query only first error
        results = module.query_error_history(
            start_time=now,
            end_time=now + timedelta(seconds=1),
        )
        assert len(results) == 1

    def test_query_error_history_with_limit(self):
        """Test querying errors with limit."""
        module = ErrorDetectionModule()

        for i in range(5):
            module.capture_exception(ValueError(f"Error {i}"), "Leaf_Node")

        results = module.query_error_history(limit=2)
        assert len(results) == 2

    def test_query_error_history_combined_filters(self):
        """Test querying errors with multiple filters."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Root_Orchestrator")
        module.capture_exception(RuntimeError("Error 3"), "Leaf_Node")

        results = module.query_error_history(
            error_type="ValueError",
            component="Leaf_Node",
        )
        assert len(results) == 1
        assert results[0].error_type == "ValueError"
        assert results[0].component == "Leaf_Node"


class TestErrorStatistics:
    """Test error statistics functionality."""

    def test_get_error_statistics_empty(self):
        """Test statistics for empty error history."""
        module = ErrorDetectionModule()

        stats = module.get_error_statistics()
        assert stats["total_errors"] == 0
        assert stats["total_occurrences"] == 0
        assert all(count == 0 for count in stats["by_severity"].values())

    def test_get_error_statistics_by_severity(self):
        """Test statistics grouped by severity."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Root_Orchestrator")
        module.capture_exception(ValueError("Error 3"), "Leaf_Node")

        stats = module.get_error_statistics()
        assert stats["total_errors"] == 3
        assert stats["by_severity"]["MEDIUM"] == 2
        assert stats["by_severity"]["CRITICAL"] == 1

    def test_get_error_statistics_by_component(self):
        """Test statistics grouped by component."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Leaf_Node")
        module.capture_exception(ValueError("Error 3"), "Root_Orchestrator")

        stats = module.get_error_statistics()
        assert stats["by_component"]["Leaf_Node"] == 2
        assert stats["by_component"]["Root_Orchestrator"] == 1

    def test_get_error_statistics_occurrence_count(self):
        """Test statistics include total occurrences."""
        module = ErrorDetectionModule()

        # Capture same error 3 times (will be deduplicated)
        exception = ValueError("Test error")
        module.capture_exception(exception, "Leaf_Node")
        module.capture_exception(exception, "Leaf_Node")
        module.capture_exception(exception, "Leaf_Node")

        stats = module.get_error_statistics()
        assert stats["total_errors"] == 1
        assert stats["total_occurrences"] == 3


class TestClearErrorHistory:
    """Test clearing error history."""

    def test_clear_error_history(self):
        """Test clearing error history."""
        module = ErrorDetectionModule()

        module.capture_exception(ValueError("Error 1"), "Leaf_Node")
        module.capture_exception(ValueError("Error 2"), "Leaf_Node")

        assert len(module.error_history) == 2

        module.clear_error_history()

        assert len(module.error_history) == 0


class TestErrorIdGeneration:
    """Test error ID generation."""

    def test_error_id_format(self):
        """Test error IDs have correct format."""
        module = ErrorDetectionModule()

        error_report = module.capture_exception(
            ValueError("Test"),
            "Leaf_Node",
        )

        assert error_report.error_id.startswith("err-")
        assert len(error_report.error_id) == 16  # "err-" + 12 hex chars

    def test_error_ids_are_unique(self):
        """Test error IDs are unique."""
        module = ErrorDetectionModule()

        error_ids = set()
        for i in range(100):
            report = module.capture_exception(
                ValueError(f"Error {i}"),
                "Leaf_Node",
            )
            error_ids.add(report.error_id)

        assert len(error_ids) == 100
