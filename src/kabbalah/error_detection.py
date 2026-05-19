"""
Error Detection Module for the Self-Healing Deployment System.

This module provides automated error detection, classification, and deduplication
for runtime exceptions and test failures. It captures full context including
exception type, message, stack trace, and execution context, then classifies
errors by severity based on component criticality and impact scope.

The module implements a 60-second deduplication window to prevent alert storms
from identical errors occurring in rapid succession.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3, 11.4
"""

import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.kabbalah.self_healing_models import ErrorReport, ErrorSeverity


logger = logging.getLogger(__name__)


class ErrorDetectionModule:
    """
    Detects, classifies, and deduplicates errors from Kabbalah components.

    This module captures runtime exceptions and test failures with full context,
    assigns unique error IDs, classifies severity based on component and scope,
    and implements a 60-second deduplication window to prevent duplicate reports.

    Attributes:
        error_history: List of all detected ErrorReport objects
        deduplication_window_seconds: Time window for deduplication (default: 60)
        critical_components: Set of component names that trigger CRITICAL severity
        high_severity_components: Set of component names that trigger HIGH severity
        _error_index: Internal index for fast deduplication lookup

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3, 11.4
    """

    def __init__(self, deduplication_window_seconds: int = 60):
        """
        Initialize the Error Detection Module.

        Args:
            deduplication_window_seconds: Time window for error deduplication (default: 60)

        Requirements: 1.1
        """
        self.error_history: List[ErrorReport] = []
        self.deduplication_window_seconds = deduplication_window_seconds

        # Component severity mappings
        self.critical_components = {
            "Intake_Node",
            "Root_Orchestrator",
            "Synthesizer",
        }
        self.high_severity_components = {
            "Domain_Orchestrator",
            "FSM_Enforcement",
        }

        # Internal index for fast deduplication lookup
        # Maps (error_type, message_hash, component) -> ErrorReport
        self._error_index: Dict[tuple, ErrorReport] = {}

        logger.info(
            "ErrorDetectionModule initialized with deduplication window: %ds",
            deduplication_window_seconds,
        )

    def capture_exception(
        self,
        exception: Exception,
        component: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ErrorReport]:
        """
        Capture a runtime exception with full context.

        Extracts exception type, message, stack trace, and execution context,
        then creates an ErrorReport with unique error_id and severity classification.
        Implements deduplication to prevent duplicate reports within time window.

        Args:
            exception: The caught exception object
            component: Name of Kabbalah component where error occurred
            context: Execution context dict (trace_id, request_id, etc.)

        Returns:
            ErrorReport if new error, None if duplicate within deduplication window

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        if context is None:
            context = {}

        # Extract exception details
        error_type = type(exception).__name__
        message = str(exception)
        stack_trace = traceback.format_exc()

        # Extract file and line number from traceback
        tb = traceback.extract_tb(exception.__traceback__)
        if tb:
            file_path = tb[-1].filename
            line_number = tb[-1].lineno
        else:
            file_path = "unknown"
            line_number = 0

        # Classify severity
        severity = self.classify_severity(
            component=component,
            error_type=error_type,
            affected_components=[component],
        )

        # Create error report
        error_report = ErrorReport(
            error_id=str(uuid.uuid4()),
            error_type=error_type,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            component=component,
            context=context,
            stack_trace=stack_trace,
            file_path=file_path,
            line_number=line_number,
            occurrence_count=1,
            status="DETECTED",
        )

        # Check for duplicates and handle deduplication
        deduplicated = self._deduplicate_error(error_report)
        if deduplicated is None:
            logger.debug(
                "Error deduplicated: %s in %s (occurrence_count incremented)",
                error_type,
                component,
            )
            return None

        # Add to history
        self.error_history.append(error_report)
        self._update_error_index(error_report)

        logger.info(
            "Exception captured: %s in %s (error_id: %s, severity: %s)",
            error_type,
            component,
            error_report.error_id,
            severity.value,
        )

        return error_report

    def capture_test_failure(
        self,
        test_name: str,
        failure_message: str,
        assertion_details: Optional[Dict[str, Any]] = None,
        test_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ErrorReport]:
        """
        Capture a test failure with assertion details.

        Creates an ErrorReport from pytest failure information including test name,
        failure message, assertion details, and test context. Classifies as HIGH
        severity by default (test failures indicate component issues).

        Args:
            test_name: Name of the test that failed
            failure_message: Failure message from pytest
            assertion_details: Dict with assertion details (expected, actual, etc.)
            test_context: Dict with test context (module, class, etc.)

        Returns:
            ErrorReport if new error, None if duplicate within deduplication window

        Requirements: 1.2, 1.3, 1.4, 1.5
        """
        if assertion_details is None:
            assertion_details = {}
        if test_context is None:
            test_context = {}

        # Extract component from test name or context
        component = test_context.get("component", "Test_Framework")

        # Create error report for test failure
        error_report = ErrorReport(
            error_id=str(uuid.uuid4()),
            error_type="TestFailure",
            message=f"Test failed: {test_name} - {failure_message}",
            severity=ErrorSeverity.HIGH,  # Test failures are HIGH severity
            timestamp=datetime.now(),
            component=component,
            context={
                "test_name": test_name,
                "assertion_details": assertion_details,
                **test_context,
            },
            stack_trace=failure_message,
            file_path=test_context.get("file_path", "unknown"),
            line_number=test_context.get("line_number", 0),
            occurrence_count=1,
            status="DETECTED",
        )

        # Check for duplicates
        deduplicated = self._deduplicate_error(error_report)
        if deduplicated is None:
            logger.debug(
                "Test failure deduplicated: %s (occurrence_count incremented)",
                test_name,
            )
            return None

        # Add to history
        self.error_history.append(error_report)
        self._update_error_index(error_report)

        logger.info(
            "Test failure captured: %s (error_id: %s, component: %s)",
            test_name,
            error_report.error_id,
            component,
        )

        return error_report

    def classify_severity(
        self,
        component: str,
        error_type: str,
        affected_components: Optional[List[str]] = None,
    ) -> ErrorSeverity:
        """
        Classify error severity based on component and scope.

        Severity classification rules:
        - CRITICAL: Errors in Intake_Node, Root_Orchestrator, or Synthesizer
        - HIGH: Errors in Domain_Orchestrator, FSM_Enforcement, or multi-component impact
        - MEDIUM: Errors in Leaf_Node or single-component failures
        - LOW: Non-blocking errors or warnings
        - INFO: Informational messages

        Args:
            component: Name of component where error occurred
            error_type: Type of error (exception class name)
            affected_components: List of components affected by this error

        Returns:
            ErrorSeverity classification

        Requirements: 11.1, 11.2, 11.3, 11.4
        """
        if affected_components is None:
            affected_components = [component]

        # Check for critical components
        if component in self.critical_components:
            return ErrorSeverity.CRITICAL

        # Check for high severity components
        if component in self.high_severity_components:
            return ErrorSeverity.HIGH

        # Check for multi-component impact (escalate severity)
        if len(affected_components) > 1:
            return ErrorSeverity.HIGH

        # Check for test failures (HIGH severity)
        if error_type == "TestFailure":
            return ErrorSeverity.HIGH

        # Check for informational errors
        if error_type in ("DeprecationWarning", "UserWarning"):
            return ErrorSeverity.INFO

        # Default: MEDIUM for leaf nodes and single-component failures
        return ErrorSeverity.MEDIUM

    def query_error_history(
        self,
        error_type: Optional[str] = None,
        component: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: Optional[int] = None,
    ) -> List[ErrorReport]:
        """
        Query error history with optional filters.

        Args:
            error_type: Filter by error type (exception class name)
            component: Filter by component name
            severity: Filter by severity level
            limit: Maximum number of results to return

        Returns:
            List of ErrorReport objects matching filters

        Requirements: 1.5
        """
        results = self.error_history

        if error_type:
            results = [e for e in results if e.error_type == error_type]

        if component:
            results = [e for e in results if e.component == component]

        if severity:
            results = [e for e in results if e.severity == severity]

        if limit:
            results = results[-limit:]

        return results

    def get_error_by_id(self, error_id: str) -> Optional[ErrorReport]:
        """
        Retrieve a specific error by error_id.

        Args:
            error_id: The unique error identifier

        Returns:
            ErrorReport if found, None otherwise

        Requirements: 1.5
        """
        for error in self.error_history:
            if error.error_id == error_id:
                return error
        return None

    def clear_history(self) -> None:
        """
        Clear all error history (useful for testing).

        Requirements: 1.5
        """
        self.error_history.clear()
        self._error_index.clear()
        logger.debug("Error history cleared")

    def _deduplicate_error(self, error_report: ErrorReport) -> Optional[ErrorReport]:
        """
        Check if identical error occurred recently and handle deduplication.

        Implements 60-second deduplication window. If identical error found within
        window, increments occurrence_count and returns None. Otherwise returns
        the error report for storage.

        Args:
            error_report: The error report to check for duplicates

        Returns:
            error_report if new error, None if duplicate within window

        Requirements: 1.6
        """
        # Create deduplication key
        key = (
            error_report.error_type,
            hash(error_report.message),
            error_report.component,
        )

        # Check if similar error exists in index
        if key in self._error_index:
            existing = self._error_index[key]
            time_diff = (
                error_report.timestamp - existing.timestamp
            ).total_seconds()

            # If within deduplication window, increment counter
            if time_diff <= self.deduplication_window_seconds:
                existing.occurrence_count += 1
                return None

        # Not a duplicate, return for storage
        return error_report

    def _update_error_index(self, error_report: ErrorReport) -> None:
        """
        Update internal error index for fast deduplication lookup.

        Args:
            error_report: The error report to index

        Requirements: 1.6
        """
        key = (
            error_report.error_type,
            hash(error_report.message),
            error_report.component,
        )
        self._error_index[key] = error_report

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected errors.

        Returns:
            Dict with error statistics (total count, by severity, by component)

        Requirements: 1.5
        """
        stats = {
            "total_errors": len(self.error_history),
            "by_severity": defaultdict(int),
            "by_component": defaultdict(int),
            "by_error_type": defaultdict(int),
        }

        for error in self.error_history:
            stats["by_severity"][error.severity.value] += 1
            stats["by_component"][error.component] += 1
            stats["by_error_type"][error.error_type] += 1

        # Convert defaultdicts to regular dicts
        stats["by_severity"] = dict(stats["by_severity"])
        stats["by_component"] = dict(stats["by_component"])
        stats["by_error_type"] = dict(stats["by_error_type"])

        return stats
