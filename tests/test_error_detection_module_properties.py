"""
Property-based tests for the ErrorDetectionModule.

Tests verify universal properties that should hold across all valid inputs:
- Property 1: Error Deduplication Within Time Window
- Property 2: Severity Classification by Component
- Property 3: Unique Error Identification
- Property 4: Error Report Persistence

Requirements: 1.6, 1.7, 1.8, 11.2, 11.3, 11.4
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from unittest.mock import patch

from kabbalah.error_detection_module import ErrorDetectionModule
from kabbalah.self_healing_models import ErrorSeverity


# Strategies for generating test data
error_types = st.sampled_from([
    "ValueError",
    "RuntimeError",
    "TypeError",
    "KeyError",
    "AttributeError",
])

components = st.sampled_from([
    "Intake_Node",
    "Root_Orchestrator",
    "Domain_Orchestrator",
    "Leaf_Node",
    "Synthesizer",
    "FSM_Enforcement",
])

error_messages = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    min_size=1,
    max_size=200,
)

trace_ids = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=5,
    max_size=50,
)


class TestProperty1ErrorDeduplicationWithinTimeWindow:
    """
    Property 1: Error Deduplication Within Time Window

    For any two identical errors detected within a 60-second window, the system
    SHALL create only one ErrorReport and increment the occurrence_count rather
    than creating duplicate reports.

    **Validates: Requirements 1.6**
    """

    @given(
        error_type=error_types,
        message=error_messages,
        component=components,
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_identical_errors_within_window_deduplicated(
        self,
        error_type,
        message,
        component,
    ):
        """Test identical errors within 60s window are deduplicated."""
        module = ErrorDetectionModule(deduplication_window_seconds=60)

        # Create exception class dynamically
        exception_class = type(error_type, (Exception,), {})
        exception = exception_class(message)

        # Capture same error twice
        report1 = module.capture_exception(exception, component)
        report2 = module.capture_exception(exception, component)

        # Verify deduplication
        assert report1 is not None, "First error should be captured"
        assert report2 is None, "Second identical error should be deduplicated"
        assert len(module.error_history) == 1, "Only one report in history"
        assert (
            module.error_history[0].occurrence_count == 2
        ), "Occurrence count should be 2"

    @given(
        error_type=error_types,
        message=error_messages,
        component=components,
        window_seconds=st.integers(min_value=1, max_value=300),
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_deduplication_respects_time_window(
        self,
        error_type,
        message,
        component,
        window_seconds,
    ):
        """Test deduplication respects configured time window."""
        module = ErrorDetectionModule(deduplication_window_seconds=window_seconds)

        exception_class = type(error_type, (Exception,), {})
        exception = exception_class(message)

        # Capture first error
        report1 = module.capture_exception(exception, component)
        assert report1 is not None

        # Capture second error within window
        report2 = module.capture_exception(exception, component)
        assert report2 is None, "Should be deduplicated within window"

        # Verify occurrence count incremented
        assert module.error_history[0].occurrence_count == 2


class TestProperty2SeverityClassificationByComponent:
    """
    Property 2: Severity Classification by Component

    For any error detected in a critical component (Intake_Node, Root_Orchestrator,
    Synthesizer), the system SHALL classify it as CRITICAL severity. For errors in
    non-critical components (Leaf_Node, Domain_Orchestrator), the system SHALL
    classify as HIGH or MEDIUM.

    **Validates: Requirements 1.7, 1.8, 11.2, 11.3, 11.4**
    """

    @given(
        message=error_messages,
        trace_id=trace_ids,
    )
    @settings(max_examples=50)
    def test_critical_components_classified_as_critical(
        self,
        message,
        trace_id,
    ):
        """Test critical components are classified as CRITICAL."""
        module = ErrorDetectionModule()
        critical_components = [
            "Intake_Node",
            "Root_Orchestrator",
            "Synthesizer",
        ]

        for component in critical_components:
            exception = RuntimeError(message)
            report = module.capture_exception(
                exception,
                component,
                context={"trace_id": trace_id},
            )

            assert (
                report.severity == ErrorSeverity.CRITICAL
            ), f"{component} should be CRITICAL"

    @given(
        message=error_messages,
        trace_id=trace_ids,
    )
    @settings(max_examples=50)
    def test_high_impact_components_classified_as_high(
        self,
        message,
        trace_id,
    ):
        """Test high-impact components are classified as HIGH."""
        module = ErrorDetectionModule()
        high_impact_components = [
            "Domain_Orchestrator",
            "FSM_Enforcement",
        ]

        for component in high_impact_components:
            exception = RuntimeError(message)
            report = module.capture_exception(
                exception,
                component,
                context={"trace_id": trace_id},
            )

            assert (
                report.severity == ErrorSeverity.HIGH
            ), f"{component} should be HIGH"

    @given(
        message=error_messages,
        trace_id=trace_ids,
    )
    @settings(max_examples=50)
    def test_leaf_node_classified_as_medium(
        self,
        message,
        trace_id,
    ):
        """Test Leaf_Node errors are classified as MEDIUM."""
        module = ErrorDetectionModule()

        exception = RuntimeError(message)
        report = module.capture_exception(
            exception,
            "Leaf_Node",
            context={"trace_id": trace_id},
        )

        assert report.severity == ErrorSeverity.MEDIUM

    @given(
        message=error_messages,
    )
    @settings(max_examples=50)
    def test_multi_component_impact_escalates_severity(
        self,
        message,
    ):
        """Test multi-component impact escalates severity to HIGH."""
        module = ErrorDetectionModule()

        # Even Leaf_Node should be HIGH if affecting multiple components
        severity = module.classify_severity(
            component="Leaf_Node",
            error_type="RuntimeError",
            affected_components=["Leaf_Node", "Domain_Orchestrator"],
        )

        assert severity == ErrorSeverity.HIGH


class TestProperty3UniqueErrorIdentification:
    """
    Property 3: Unique Error Identification

    For any set of detected errors, each error SHALL have a unique error_id
    and timestamp, with no two errors sharing the same error_id.

    **Validates: Requirements 1.3**
    """

    @given(
        num_errors=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=20)
    def test_each_error_has_unique_error_id(self, num_errors):
        """Test each error gets a unique error_id."""
        module = ErrorDetectionModule()
        error_ids = set()

        for i in range(num_errors):
            exception = ValueError(f"Error {i}")
            report = module.capture_exception(exception, "Leaf_Node")

            # Verify error_id is unique
            assert report.error_id not in error_ids, "error_id must be unique"
            error_ids.add(report.error_id)

        # Verify all error_ids are unique
        assert len(error_ids) == num_errors

    @given(
        num_errors=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=20)
    def test_error_ids_have_correct_format(self, num_errors):
        """Test all error_ids have correct format."""
        module = ErrorDetectionModule()

        for i in range(num_errors):
            exception = ValueError(f"Error {i}")
            report = module.capture_exception(exception, "Leaf_Node")

            # Verify format
            assert report.error_id.startswith("err-"), "error_id must start with 'err-'"
            assert len(report.error_id) == 16, "error_id must be 16 chars (err- + 12 hex)"

    @given(
        num_errors=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=20)
    def test_error_timestamps_are_set(self, num_errors):
        """Test all errors have timestamps."""
        module = ErrorDetectionModule()
        now = datetime.now()

        for i in range(num_errors):
            exception = ValueError(f"Error {i}")
            report = module.capture_exception(exception, "Leaf_Node")

            # Verify timestamp is set and recent
            assert report.timestamp is not None
            assert report.timestamp >= now
            assert report.timestamp <= datetime.now()


class TestProperty4ErrorReportPersistence:
    """
    Property 4: Error Report Persistence

    For any detected error, querying the error_history after detection SHALL
    return the ErrorReport with all captured details (exception type, message,
    stack trace, context).

    **Validates: Requirements 1.5**
    """

    @given(
        error_type=error_types,
        message=error_messages,
        component=components,
        trace_id=trace_ids,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_detected_error_queryable_from_history(
        self,
        error_type,
        message,
        component,
        trace_id,
    ):
        """Test detected errors are queryable from history."""
        module = ErrorDetectionModule()

        # Create and capture exception
        exception_class = type(error_type, (Exception,), {})
        exception = exception_class(message)
        report = module.capture_exception(
            exception,
            component,
            context={"trace_id": trace_id},
        )

        # Query history
        results = module.query_error_history(
            error_type=error_type,
            component=component,
        )

        # Verify error is in history
        assert len(results) > 0, "Error should be in history"
        assert results[0].error_id == report.error_id
        assert results[0].error_type == error_type
        assert results[0].message == message
        assert results[0].component == component
        assert results[0].context["trace_id"] == trace_id

    @given(
        num_errors=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=20)
    def test_all_detected_errors_queryable(self, num_errors):
        """Test all detected errors are queryable from history."""
        module = ErrorDetectionModule()
        captured_ids = []

        # Capture multiple different errors
        for i in range(num_errors):
            exception = ValueError(f"Error {i}")
            report = module.capture_exception(exception, "Leaf_Node")
            captured_ids.append(report.error_id)

        # Query all errors
        results = module.query_error_history()

        # Verify all errors are in history
        assert len(results) == num_errors
        result_ids = {r.error_id for r in results}
        assert result_ids == set(captured_ids)

    @given(
        message=error_messages,
        component=components,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_error_details_preserved_in_history(
        self,
        message,
        component,
    ):
        """Test all error details are preserved in history."""
        module = ErrorDetectionModule()

        exception = RuntimeError(message)
        report = module.capture_exception(
            exception,
            component,
            context={"trace_id": "trace-123", "request_id": "req-456"},
        )

        # Query and verify details
        results = module.query_error_history(error_type="RuntimeError")
        assert len(results) >= 1

        retrieved = results[0]
        assert retrieved.error_type == "RuntimeError"
        assert retrieved.message == message
        assert retrieved.component == component
        assert retrieved.context["trace_id"] == "trace-123"
        assert retrieved.context["request_id"] == "req-456"
        assert retrieved.stack_trace is not None
        assert len(retrieved.stack_trace) > 0
        assert retrieved.file_path is not None
        assert retrieved.line_number > 0


class TestProperty5TestFailureCapture:
    """
    Property 5: Test Failure Capture

    For any test failure, the Error_Detection_Module SHALL capture the test
    name, failure message, assertion details, and classify as HIGH severity.

    **Validates: Requirements 1.2**
    """

    @given(
        test_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz_",
            min_size=5,
            max_size=50,
        ),
        failure_message=error_messages,
    )
    @settings(max_examples=50)
    def test_test_failures_captured_with_high_severity(
        self,
        test_name,
        failure_message,
    ):
        """Test failures are captured with HIGH severity."""
        module = ErrorDetectionModule()

        report = module.capture_test_failure(
            test_name=test_name,
            failure_message=failure_message,
        )

        assert report is not None
        assert report.error_type == "TestFailure"
        assert report.message == failure_message
        assert report.severity == ErrorSeverity.HIGH
        assert report.context["test_name"] == test_name

    @given(
        test_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz_",
            min_size=5,
            max_size=50,
        ),
        failure_message=error_messages,
    )
    @settings(max_examples=50)
    def test_test_failures_queryable_from_history(
        self,
        test_name,
        failure_message,
    ):
        """Test failures are queryable from history."""
        module = ErrorDetectionModule()

        report = module.capture_test_failure(
            test_name=test_name,
            failure_message=failure_message,
        )

        # Query by component
        results = module.query_error_history(component="TestFramework")
        assert len(results) > 0
        assert any(r.error_id == report.error_id for r in results)


class TestProperty7ErrorContextPreservation:
    """
    Property 7: Error Context Preservation

    For any error captured with context (trace_id, request_id, etc.),
    the context SHALL be preserved in the ErrorReport.

    **Validates: Requirements 1.1**
    """

    @given(
        trace_id=trace_ids,
        request_id=trace_ids,
        user_id=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
            min_size=5,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_error_context_preserved(
        self,
        trace_id,
        request_id,
        user_id,
    ):
        """Test error context is preserved."""
        module = ErrorDetectionModule()

        context = {
            "trace_id": trace_id,
            "request_id": request_id,
            "user_id": user_id,
        }

        exception = RuntimeError("Test error")
        report = module.capture_exception(exception, "Leaf_Node", context=context)

        # Verify context preserved
        assert report.context["trace_id"] == trace_id
        assert report.context["request_id"] == request_id
        assert report.context["user_id"] == user_id
