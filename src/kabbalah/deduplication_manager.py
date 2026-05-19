"""
Deduplication Manager for the Self-Healing Deployment System.

This module provides comprehensive error deduplication management with configurable
matching criteria, occurrence counter tracking, and query interfaces. It manages
the deduplication window, error comparison logic, and maintains statistics about
deduplicated errors.

The module implements:
- Configurable deduplication window (default: 60 seconds)
- Error comparison by type, message, and component
- Occurrence counter increment for duplicates
- Deduplication query interface (find_duplicates, get_deduplication_stats)
- Configurable deduplication rules
- Comprehensive error handling and logging

Requirements: 1.6, 11.6
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from kabbalah.self_healing_models import ErrorReport, ErrorSeverity

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationRule:
    """
    Configuration for error deduplication matching criteria.

    Defines which fields are used to determine if two errors are identical
    for deduplication purposes.

    Attributes:
        match_error_type: Include error_type in comparison (default: True)
        match_message: Include message in comparison (default: True)
        match_component: Include component in comparison (default: True)
        match_file_path: Include file_path in comparison (default: False)
        match_line_number: Include line_number in comparison (default: False)
        message_similarity_threshold: Threshold for fuzzy message matching (0.0-1.0)
        use_fuzzy_matching: Enable fuzzy message matching (default: False)

    Requirements: 1.6
    """

    match_error_type: bool = True
    """Include error_type in comparison"""

    match_message: bool = True
    """Include message in comparison"""

    match_component: bool = True
    """Include component in comparison"""

    match_file_path: bool = False
    """Include file_path in comparison"""

    match_line_number: bool = False
    """Include line_number in comparison"""

    message_similarity_threshold: float = 0.8
    """Threshold for fuzzy message matching (0.0-1.0)"""

    use_fuzzy_matching: bool = False
    """Enable fuzzy message matching"""


@dataclass
class DeduplicationStats:
    """
    Statistics about deduplicated errors.

    Tracks deduplication activity including total errors, deduplicated count,
    and occurrence counts.

    Attributes:
        total_errors_detected: Total number of unique errors detected
        total_duplicates_found: Total number of duplicate errors found
        total_occurrences: Total occurrences including duplicates
        errors_by_type: Count of errors by error_type
        errors_by_component: Count of errors by component
        deduplication_window_seconds: Current deduplication window
        timestamp: When statistics were generated

    Requirements: 1.6
    """

    total_errors_detected: int = 0
    """Total number of unique errors detected"""

    total_duplicates_found: int = 0
    """Total number of duplicate errors found"""

    total_occurrences: int = 0
    """Total occurrences including duplicates"""

    errors_by_type: Dict[str, int] = field(default_factory=dict)
    """Count of errors by error_type"""

    errors_by_component: Dict[str, int] = field(default_factory=dict)
    """Count of errors by component"""

    deduplication_window_seconds: int = 60
    """Current deduplication window"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When statistics were generated"""


@dataclass
class DuplicateGroup:
    """
    Group of duplicate errors.

    Represents a set of identical errors that have been deduplicated,
    including the original error and all duplicates.

    Attributes:
        original_error: The first error in the group
        duplicate_count: Number of duplicates found
        occurrence_count: Total occurrences (1 + duplicate_count)
        first_occurrence: Timestamp of first occurrence
        last_occurrence: Timestamp of most recent occurrence
        duplicate_timestamps: List of timestamps for each duplicate

    Requirements: 1.6
    """

    original_error: ErrorReport
    """The first error in the group"""

    duplicate_count: int = 0
    """Number of duplicates found"""

    occurrence_count: int = 1
    """Total occurrences (1 + duplicate_count)"""

    first_occurrence: datetime = field(default_factory=datetime.now)
    """Timestamp of first occurrence"""

    last_occurrence: datetime = field(default_factory=datetime.now)
    """Timestamp of most recent occurrence"""

    duplicate_timestamps: List[datetime] = field(default_factory=list)
    """List of timestamps for each duplicate"""


class DeduplicationManager:
    """
    Manages error deduplication with configurable matching criteria.

    This manager handles the deduplication of errors within a configurable
    time window. It supports multiple deduplication rules, occurrence counter
    tracking, and provides query interfaces for finding duplicates and
    retrieving deduplication statistics.

    Attributes:
        deduplication_window_seconds: Time window for deduplication (default: 60)
        deduplication_rule: Rule for determining error identity
        error_groups: Dict mapping error signatures to DuplicateGroup objects
        error_history: List of all errors (original + duplicates)

    Requirements: 1.6, 11.6
    """

    def __init__(
        self,
        deduplication_window_seconds: int = 60,
        deduplication_rule: Optional[DeduplicationRule] = None,
    ):
        """
        Initialize the DeduplicationManager.

        Args:
            deduplication_window_seconds: Time window for deduplication (default: 60)
            deduplication_rule: Rule for determining error identity (default: standard)

        Requirements: 1.6
        """
        self.deduplication_window_seconds = deduplication_window_seconds
        self.deduplication_rule = (
            deduplication_rule or DeduplicationRule()
        )
        self.error_groups: Dict[str, DuplicateGroup] = {}
        self.error_history: List[ErrorReport] = []

        logger.info(
            f"DeduplicationManager initialized with window: "
            f"{deduplication_window_seconds}s"
        )

    def set_deduplication_rule(
        self,
        rule: DeduplicationRule,
    ) -> None:
        """
        Configure deduplication matching criteria.

        Allows runtime configuration of which fields are used to determine
        if two errors are identical.

        Args:
            rule: DeduplicationRule specifying matching criteria

        Requirements: 1.6
        """
        self.deduplication_rule = rule
        logger.info(
            f"Deduplication rule updated: "
            f"type={rule.match_error_type}, "
            f"message={rule.match_message}, "
            f"component={rule.match_component}"
        )

    def set_deduplication_window(
        self,
        window_seconds: int,
    ) -> None:
        """
        Configure deduplication time window.

        Args:
            window_seconds: Time window in seconds

        Requirements: 1.6
        """
        if window_seconds <= 0:
            raise ValueError("Deduplication window must be positive")

        self.deduplication_window_seconds = window_seconds
        logger.info(f"Deduplication window updated to {window_seconds}s")

    def compare_errors(
        self,
        error1: ErrorReport,
        error2: ErrorReport,
    ) -> bool:
        """
        Compare two errors for identity based on deduplication rule.

        Compares errors using the configured deduplication rule to determine
        if they are identical for deduplication purposes.

        Args:
            error1: First error to compare
            error2: Second error to compare

        Returns:
            True if errors are identical according to rule, False otherwise

        Requirements: 1.6
        """
        # Check error type
        if self.deduplication_rule.match_error_type:
            if error1.error_type != error2.error_type:
                return False

        # Check message
        if self.deduplication_rule.match_message:
            if self.deduplication_rule.use_fuzzy_matching:
                similarity = self._calculate_message_similarity(
                    error1.message,
                    error2.message,
                )
                if (
                    similarity
                    < self.deduplication_rule.message_similarity_threshold
                ):
                    return False
            else:
                if error1.message != error2.message:
                    return False

        # Check component
        if self.deduplication_rule.match_component:
            if error1.component != error2.component:
                return False

        # Check file path
        if self.deduplication_rule.match_file_path:
            if error1.file_path != error2.file_path:
                return False

        # Check line number
        if self.deduplication_rule.match_line_number:
            if error1.line_number != error2.line_number:
                return False

        return True

    def _calculate_message_similarity(
        self,
        message1: str,
        message2: str,
    ) -> float:
        """
        Calculate similarity between two error messages.

        Uses Levenshtein distance to calculate similarity score.

        Args:
            message1: First message
            message2: Second message

        Returns:
            Similarity score (0.0-1.0)

        Requirements: 1.6
        """
        # Simple Levenshtein distance implementation
        if message1 == message2:
            return 1.0

        len1, len2 = len(message1), len(message2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Create distance matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if message1[i - 1] == message2[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1]
                else:
                    matrix[i][j] = 1 + min(
                        matrix[i - 1][j],
                        matrix[i][j - 1],
                        matrix[i - 1][j - 1],
                    )

        distance = matrix[len1][len2]
        max_len = max(len1, len2)
        similarity = 1.0 - (distance / max_len)

        return max(0.0, min(1.0, similarity))

    def _generate_error_signature(
        self,
        error: ErrorReport,
    ) -> str:
        """
        Generate a unique signature for an error based on deduplication rule.

        Args:
            error: Error to generate signature for

        Returns:
            String signature for the error

        Requirements: 1.6
        """
        parts = []

        if self.deduplication_rule.match_error_type:
            parts.append(f"type:{error.error_type}")

        if self.deduplication_rule.match_message:
            parts.append(f"msg:{error.message}")

        if self.deduplication_rule.match_component:
            parts.append(f"comp:{error.component}")

        if self.deduplication_rule.match_file_path:
            parts.append(f"file:{error.file_path}")

        if self.deduplication_rule.match_line_number:
            parts.append(f"line:{error.line_number}")

        return "|".join(parts)

    def process_error(
        self,
        error: ErrorReport,
    ) -> Tuple[bool, Optional[ErrorReport]]:
        """
        Process an error for deduplication.

        Checks if the error is a duplicate of a recent error. If so,
        increments the occurrence counter and returns (True, original_error).
        Otherwise, creates a new error group and returns (False, error).

        Args:
            error: Error to process

        Returns:
            Tuple of (is_duplicate, error_or_original)
            - If duplicate: (True, original_error)
            - If new: (False, error)

        Requirements: 1.6
        """
        signature = self._generate_error_signature(error)
        cutoff_time = datetime.now() - timedelta(
            seconds=self.deduplication_window_seconds
        )

        # Check if error group exists and is within window
        if signature in self.error_groups:
            group = self.error_groups[signature]

            # Check if group is still within deduplication window
            if group.last_occurrence >= cutoff_time:
                # Increment occurrence counter
                group.duplicate_count += 1
                group.occurrence_count += 1
                group.last_occurrence = datetime.now()
                group.duplicate_timestamps.append(datetime.now())

                # Update original error's occurrence count
                group.original_error.occurrence_count += 1

                logger.debug(
                    f"Error deduplicated: {error.error_type} in {error.component} "
                    f"(occurrence_count: {group.original_error.occurrence_count})"
                )

                self.error_history.append(error)
                return (True, group.original_error)
            else:
                # Window expired, create new group
                del self.error_groups[signature]

        # Create new error group
        group = DuplicateGroup(
            original_error=error,
            duplicate_count=0,
            occurrence_count=1,
            first_occurrence=datetime.now(),
            last_occurrence=datetime.now(),
            duplicate_timestamps=[],
        )

        self.error_groups[signature] = group
        self.error_history.append(error)

        logger.debug(
            f"New error group created: {error.error_type} in {error.component}"
        )

        return (False, error)

    def find_duplicates(
        self,
        error: ErrorReport,
        window_seconds: Optional[int] = None,
    ) -> List[ErrorReport]:
        """
        Find all duplicate errors for a given error.

        Searches the error history for all errors that match the given error
        according to the deduplication rule, within the specified window.

        Args:
            error: Error to find duplicates for
            window_seconds: Override deduplication window (default: instance setting)

        Returns:
            List of duplicate ErrorReport objects (not including original)

        Requirements: 1.6
        """
        if window_seconds is None:
            window_seconds = self.deduplication_window_seconds

        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        duplicates = []

        for other_error in self.error_history:
            # Skip the original error
            if other_error.error_id == error.error_id:
                continue

            # Check time window
            if other_error.timestamp < cutoff_time:
                continue

            # Check if errors match
            if self.compare_errors(error, other_error):
                duplicates.append(other_error)

        return duplicates

    def get_duplicate_group(
        self,
        error: ErrorReport,
    ) -> Optional[DuplicateGroup]:
        """
        Get the duplicate group for an error.

        Args:
            error: Error to get group for

        Returns:
            DuplicateGroup if error is in a group, None otherwise

        Requirements: 1.6
        """
        signature = self._generate_error_signature(error)
        return self.error_groups.get(signature)

    def get_deduplication_stats(self) -> DeduplicationStats:
        """
        Get deduplication statistics.

        Returns statistics about deduplication activity including total errors,
        duplicates found, and occurrence counts.

        Returns:
            DeduplicationStats object with current statistics

        Requirements: 1.6
        """
        stats = DeduplicationStats(
            total_errors_detected=len(self.error_groups),
            total_duplicates_found=sum(
                group.duplicate_count
                for group in self.error_groups.values()
            ),
            total_occurrences=sum(
                group.occurrence_count
                for group in self.error_groups.values()
            ),
            deduplication_window_seconds=self.deduplication_window_seconds,
            timestamp=datetime.now(),
        )

        # Count by error type
        for group in self.error_groups.values():
            error_type = group.original_error.error_type
            if error_type not in stats.errors_by_type:
                stats.errors_by_type[error_type] = 0
            stats.errors_by_type[error_type] += 1

        # Count by component
        for group in self.error_groups.values():
            component = group.original_error.component
            if component not in stats.errors_by_component:
                stats.errors_by_component[component] = 0
            stats.errors_by_component[component] += 1

        return stats

    def get_all_duplicate_groups(self) -> List[DuplicateGroup]:
        """
        Get all duplicate groups.

        Returns:
            List of all DuplicateGroup objects

        Requirements: 1.6
        """
        return list(self.error_groups.values())

    def get_duplicate_groups_by_component(
        self,
        component: str,
    ) -> List[DuplicateGroup]:
        """
        Get duplicate groups for a specific component.

        Args:
            component: Component name to filter by

        Returns:
            List of DuplicateGroup objects for the component

        Requirements: 1.6
        """
        return [
            group
            for group in self.error_groups.values()
            if group.original_error.component == component
        ]

    def get_duplicate_groups_by_error_type(
        self,
        error_type: str,
    ) -> List[DuplicateGroup]:
        """
        Get duplicate groups for a specific error type.

        Args:
            error_type: Error type to filter by

        Returns:
            List of DuplicateGroup objects for the error type

        Requirements: 1.6
        """
        return [
            group
            for group in self.error_groups.values()
            if group.original_error.error_type == error_type
        ]

    def get_duplicate_groups_by_severity(
        self,
        severity: ErrorSeverity,
    ) -> List[DuplicateGroup]:
        """
        Get duplicate groups for a specific severity level.

        Args:
            severity: ErrorSeverity to filter by

        Returns:
            List of DuplicateGroup objects for the severity

        Requirements: 1.6
        """
        return [
            group
            for group in self.error_groups.values()
            if group.original_error.severity == severity
        ]

    def clear_expired_groups(self) -> int:
        """
        Remove error groups that have expired from the deduplication window.

        Returns:
            Number of groups removed

        Requirements: 1.6
        """
        cutoff_time = datetime.now() - timedelta(
            seconds=self.deduplication_window_seconds
        )

        expired_signatures = [
            sig
            for sig, group in self.error_groups.items()
            if group.last_occurrence < cutoff_time
        ]

        for sig in expired_signatures:
            del self.error_groups[sig]

        if expired_signatures:
            logger.debug(
                f"Cleared {len(expired_signatures)} expired error groups"
            )

        return len(expired_signatures)

    def clear_all(self) -> None:
        """
        Clear all error groups and history.

        Used for testing and resetting the manager state.

        Requirements: 1.6
        """
        self.error_groups.clear()
        self.error_history.clear()
        logger.info("DeduplicationManager cleared")
