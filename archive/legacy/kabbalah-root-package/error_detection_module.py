"""
Error Detection Module for the Self-Healing Deployment System.

This module provides comprehensive error detection, classification, and deduplication
for the Kabbalah multi-agent orchestration platform. It captures runtime exceptions
from all components, test failures from pytest, classifies errors by severity based
on component criticality, and maintains an in-memory error history with deduplication.

The module implements:
- Exception capture with full context (trace_id, request_id, stack trace)
- Test failure capture with assertion details
- Severity classification based on component type and impact scope
- Error deduplication within 60-second time windows
- In-memory error history storage with query interface

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3, 11.4
"""

import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from kabbalah.self_healing_models import ErrorReport, ErrorSeverity

logger = logging.getLogger(__name__)


class ErrorDetectionModule:
    """
    Detects, classifies, and deduplicates errors from Kabbalah components and tests.

    This module serves as the entry point for error detection in the self-healing system.
    It captures exceptions from component error hooks and test failures from pytest,
    assigns unique error IDs, classifies severity based on component and scope,
    deduplicates identical errors within a 60-second window, and maintains an
    in-memory error history for later analysis and learning.

    Attributes:
        error_history: List of ErrorReport objects, ordered by timestamp
        deduplication_window_seconds: Time window for error deduplication (default: 60)
        critical_components: Set of component names that trigger CRITICAL severity
        high_impact_components: Set of component names that trigger HIGH severity
        medium_impact_components: Set of component names that trigger MEDIUM severity

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3, 11.4
    """

    def __init__(self, deduplication_window_seconds: int = 60):
        """
        Initialize the ErrorDetectionModule.

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
        self.high_impact_components = {
            "Domain_Orchestrator",
            "FSM_Enforcement",
        }
        self.medium_impact_components = {
            "Leaf_Node",
        }

        logger.info(
            f"ErrorDetectionModule initialized with deduplication window: "
            f"{deduplication_window_seconds}s"
        )

    def capture_exception(
        self,
        exception: Exception,
        component: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ErrorReport]:
        """
        Capture a runtime exception with full context.

        Captures the exception type, message, stack trace, and execution context
        (trace_id, request_id, etc.). Classifies severity based on component and
        scope. Deduplicates identical errors within the time window.

        Args:
            exception: The caught exception
            component: Name of component where error occurred
            context: Execution context dict (trace_id, request_id, etc.)

        Returns:
            ErrorReport with unique error_id and severity classification,
            or None if error was deduplicated

        Requirements: 1.1, 1.3, 1.4, 1.5
        """
        if context is None:
            context = {}

        # Extract exception details
        error_type = type(exception).__name__
        message = str(exception)
        stack_trace = traceback.format_exc()

        # Extract file and line number from traceback
        file_path = "unknown"
        line_number = 0
        tb = traceback.extract_tb(exception.__traceback__)
        if tb:
            file_path = tb[-1].filename
            line_number = tb[-1].lineno

        # Classify severity
        severity = self.classify_severity(
            component=component,
            error_type=error_type,
            affected_components=[component],
        )

        # Create error report
        error_report = ErrorReport(
            error_id=self._generate_error_id(),
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

        # Check for deduplication
        deduplicated_report = self.deduplicate_error(error_report)
        if deduplicated_report is None:
            logger.debug(
                f"Error deduplicated: {error_type} in {component} "
                f"(occurrence count incremented)"
            )
            return None

        # Add to history
        self.error_history.append(error_report)
        logger.info(
            f"Exception captured: {error_type} in {component} "
            f"(severity: {severity.value}, error_id: {error_report.error_id})"
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

        Captures test failures from pytest integration, including test name,
        failure message, assertion details, and test context. Classifies as
        HIGH severity (test failures indicate system issues).

        Args:
            test_name: Name of the test that failed
            failure_message: Failure message from test framework
            assertion_details: Dict with assertion details (expected, actual, etc.)
            test_context: Dict with test context (module, class, etc.)

        Returns:
            ErrorReport with unique error_id and HIGH severity,
            or None if error was deduplicated

        Requirements: 1.2, 1.3, 1.4, 1.5
        """
        if assertion_details is None:
            assertion_details = {}
        if test_context is None:
            test_context = {}

        # Create context with test details
        context = {
            "test_name": test_name,
            "assertion_details": assertion_details,
            **test_context,
        }

        # Test failures are always HIGH severity
        severity = ErrorSeverity.HIGH

        # Create error report
        error_report = ErrorReport(
            error_id=self._generate_error_id(),
            error_type="TestFailure",
            message=failure_message,
            severity=severity,
            timestamp=datetime.now(),
            component="TestFramework",
            context=context,
            stack_trace=failure_message,  # Test failure message as stack trace
            file_path=test_context.get("file_path", "unknown"),
            line_number=test_context.get("line_number", 0),
            occurrence_count=1,
            status="DETECTED",
        )

        # Check for deduplication
        deduplicated_report = self.deduplicate_error(error_report)
        if deduplicated_report is None:
            logger.debug(
                f"Test failure deduplicated: {test_name} "
                f"(occurrence count incremented)"
            )
            return None

        # Add to history
        self.error_history.append(error_report)
        logger.info(
            f"Test failure captured: {test_name} "
            f"(error_id: {error_report.error_id})"
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
        - LOW: Warnings or non-blocking errors
        - INFO: Informational messages

        Args:
            component: Name of component where error occurred
            error_type: Exception class name or error type
            affected_components: List of components affected by this error

        Returns:
            ErrorSeverity classification

        Requirements: 11.2, 11.3, 11.4
        """
        if affected_components is None:
            affected_components = [component]

        # Check for critical components
        if component in self.critical_components:
            return ErrorSeverity.CRITICAL

        # Check for multi-component impact (escalate to HIGH)
        if len(affected_components) > 1:
            return ErrorSeverity.HIGH

        # Check for high-impact components
        if component in self.high_impact_components:
            return ErrorSeverity.HIGH

        # Check for medium-impact components
        if component in self.medium_impact_components:
            return ErrorSeverity.MEDIUM

        # Check for informational error types
        if error_type in ("DeprecationWarning", "UserWarning"):
            return ErrorSeverity.INFO

        # Default to MEDIUM for unknown components
        return ErrorSeverity.MEDIUM

    def deduplicate_error(
        self,
        error_report: ErrorReport,
        window_seconds: Optional[int] = None,
    ) -> Optional[ErrorReport]:
        """
        Check if identical error occurred recently and deduplicate.

        Searches error history for identical errors (same error_type, message,
        and component) within the deduplication window. If found, increments
        the occurrence_count on the existing report and returns None.
        Otherwise, returns the error_report for addition to history.

        Args:
            error_report: ErrorReport to check for deduplication
            window_seconds: Override deduplication window (default: instance setting)

        Returns:
            None if error was deduplicated (incremented existing report),
            else returns the error_report for addition to history

        Requirements: 1.6, 11.6
        """
        if window_seconds is None:
            window_seconds = self.deduplication_window_seconds

        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)

        # Search for identical error in recent history
        for existing_report in reversed(self.error_history):
            # Only check within time window
            if existing_report.timestamp < cutoff_time:
                break

            # Check if error is identical
            if (
                existing_report.error_type == error_report.error_type
                and existing_report.message == error_report.message
                and existing_report.component == error_report.component
            ):
                # Increment occurrence counter
                existing_report.occurrence_count += 1
                logger.debug(
                    f"Error deduplicated: {error_report.error_type} "
                    f"(occurrence_count: {existing_report.occurrence_count})"
                )
                return None

        # No duplicate found, return report for addition to history
        return error_report

    def query_error_history(
        self,
        error_type: Optional[str] = None,
        component: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ErrorReport]:
        """
        Query error history with optional filters.

        Allows querying the error history with various filters to find
        specific errors for analysis and learning.

        Args:
            error_type: Filter by error type (e.g., "ValueError")
            component: Filter by component name
            severity: Filter by ErrorSeverity
            start_time: Filter errors after this time
            end_time: Filter errors before this time
            limit: Maximum number of results to return

        Returns:
            List of ErrorReport objects matching the filters

        Requirements: 1.5
        """
        results = []

        for error_report in self.error_history:
            # Apply filters
            if error_type and error_report.error_type != error_type:
                continue
            if component and error_report.component != component:
                continue
            if severity and error_report.severity != severity:
                continue
            if start_time and error_report.timestamp < start_time:
                continue
            if end_time and error_report.timestamp > end_time:
                continue

            results.append(error_report)

        # Apply limit (most recent first)
        if limit:
            results = results[-limit:]

        return results

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected errors.

        Returns:
            Dict with error statistics including counts by severity and component

        Requirements: 1.5
        """
        stats = {
            "total_errors": len(self.error_history),
            "by_severity": {},
            "by_component": {},
            "total_occurrences": sum(
                e.occurrence_count for e in self.error_history
            ),
        }

        # Count by severity
        for severity in ErrorSeverity:
            count = sum(
                1 for e in self.error_history if e.severity == severity
            )
            stats["by_severity"][severity.value] = count

        # Count by component
        for error_report in self.error_history:
            component = error_report.component
            if component not in stats["by_component"]:
                stats["by_component"][component] = 0
            stats["by_component"][component] += 1

        return stats

    def clear_error_history(self) -> None:
        """
        Clear all error history.

        Used for testing and resetting the module state.
        """
        self.error_history.clear()
        logger.info("Error history cleared")

    def _generate_error_id(self) -> str:
        """
        Generate a unique error ID.

        Returns:
            UUID string for the error

        Requirements: 1.3
        """
        return f"err-{uuid.uuid4().hex[:12]}"
