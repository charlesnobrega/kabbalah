"""FSM Enforcement Module for runtime hardening.

This module enforces operational modes (BOOTSTRAP, DAY1, DAY2) at runtime,
ensuring that bootstrap operations cannot occur in production (DAY2) mode.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import os
import time


class OperationalMode(Enum):
    """Operational modes for the system."""
    BOOTSTRAP = "BOOTSTRAP"
    DAY1 = "DAY1"
    DAY2 = "DAY2"


class OperationType(Enum):
    """Types of operations that can be performed."""
    BOOTSTRAP_OPERATION = "bootstrap_operation"
    AGENT_INITIALIZATION = "agent_initialization"
    MEMORY_RESET = "memory_reset"
    CONFIGURATION_CHANGE = "configuration_change"
    QUERY_OPERATION = "query_operation"
    READ_OPERATION = "read_operation"
    TOOL_EXECUTION = "tool_execution"
    PROJECT_REQUEST = "project_request"


@dataclass
class Operation:
    """Represents an operation to be checked."""
    operation_type: OperationType
    operation_name: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ModeTransitionRecord:
    """Record of a mode transition."""
    from_mode: OperationalMode
    to_mode: OperationalMode
    timestamp: float
    reason: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class OperationViolation:
    """Record of an operation violation."""
    operation: Operation
    current_mode: OperationalMode
    timestamp: float
    violation_type: str
    message: str


class FSMEnforcementModule:
    """Enforces operational modes at runtime.
    
    This module ensures that:
    - Bootstrap operations are blocked in DAY2 mode
    - Mode transitions are validated and logged
    - All violations are recorded in an immutable audit log
    - The system operates within the constraints of its current mode
    """

    # Bootstrap operations that are blocked in DAY2
    BOOTSTRAP_OPERATIONS = {
        OperationType.BOOTSTRAP_OPERATION,
        OperationType.AGENT_INITIALIZATION,
        OperationType.MEMORY_RESET,
        OperationType.CONFIGURATION_CHANGE,
    }

    # Operations allowed in each mode
    MODE_PERMISSIONS = {
        OperationalMode.BOOTSTRAP: {
            OperationType.BOOTSTRAP_OPERATION,
            OperationType.AGENT_INITIALIZATION,
            OperationType.MEMORY_RESET,
            OperationType.CONFIGURATION_CHANGE,
            OperationType.QUERY_OPERATION,
            OperationType.READ_OPERATION,
            OperationType.TOOL_EXECUTION,
            OperationType.PROJECT_REQUEST,
        },
        OperationalMode.DAY1: {
            OperationType.BOOTSTRAP_OPERATION,
            OperationType.AGENT_INITIALIZATION,
            OperationType.MEMORY_RESET,
            OperationType.CONFIGURATION_CHANGE,
            OperationType.QUERY_OPERATION,
            OperationType.READ_OPERATION,
            OperationType.TOOL_EXECUTION,
            OperationType.PROJECT_REQUEST,
        },
        OperationalMode.DAY2: {
            OperationType.QUERY_OPERATION,
            OperationType.READ_OPERATION,
            OperationType.TOOL_EXECUTION,
            OperationType.PROJECT_REQUEST,
        },
    }

    def __init__(self):
        """Initialize the FSM Enforcement Module."""
        self._current_mode = self._detect_initial_mode()
        self._transition_log: List[ModeTransitionRecord] = []
        self._violation_log: List[OperationViolation] = []

    def _detect_initial_mode(self) -> OperationalMode:
        """Detect the initial operational mode from environment.
        
        Returns:
            OperationalMode: The detected operational mode
        """
        mode_str = os.environ.get("V5_RUNTIME_MODE", "BOOTSTRAP").upper()
        try:
            return OperationalMode[mode_str]
        except KeyError:
            # Default to BOOTSTRAP if invalid mode is specified
            return OperationalMode.BOOTSTRAP

    @property
    def current_mode(self) -> OperationalMode:
        """Get the current operational mode.
        
        Returns:
            OperationalMode: The current mode
        """
        return self._current_mode

    @property
    def transition_log(self) -> List[ModeTransitionRecord]:
        """Get the immutable transition log.
        
        Returns:
            List[ModeTransitionRecord]: Copy of the transition log
        """
        return list(self._transition_log)

    @property
    def violation_log(self) -> List[OperationViolation]:
        """Get the immutable violation log.
        
        Returns:
            List[OperationViolation]: Copy of the violation log
        """
        return list(self._violation_log)

    def check_operation_allowed(
        self,
        operation: Operation,
        current_mode: Optional[OperationalMode] = None
    ) -> bool:
        """Check if an operation is allowed in the current mode.
        
        Args:
            operation: The operation to check
            current_mode: Optional mode to check against (defaults to current mode)
            
        Returns:
            bool: True if the operation is allowed, False otherwise
        """
        mode = current_mode or self._current_mode
        allowed_operations = self.MODE_PERMISSIONS.get(mode, set())
        return operation.operation_type in allowed_operations

    def check_operation_allowed_with_logging(
        self,
        operation: Operation,
        current_mode: Optional[OperationalMode] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if an operation is allowed and log violations.
        
        Args:
            operation: The operation to check
            current_mode: Optional mode to check against (defaults to current mode)
            
        Returns:
            Tuple[bool, Optional[str]]: (is_allowed, error_message)
        """
        mode = current_mode or self._current_mode
        is_allowed = self.check_operation_allowed(operation, mode)

        if not is_allowed:
            violation_type = "OPERATION_BLOCKED"
            if operation.operation_type in self.BOOTSTRAP_OPERATIONS and mode == OperationalMode.DAY2:
                violation_type = "BOOTSTRAP_OPERATION_IN_DAY2"

            message = (
                f"Operation '{operation.operation_name}' "
                f"(type: {operation.operation_type.value}) "
                f"is not allowed in {mode.value} mode"
            )

            violation = OperationViolation(
                operation=operation,
                current_mode=mode,
                timestamp=time.time(),
                violation_type=violation_type,
                message=message
            )
            self._violation_log.append(violation)

        return is_allowed, None if is_allowed else f"Operation not allowed in {mode.value} mode"

    def transition_mode(
        self,
        from_mode: OperationalMode,
        to_mode: OperationalMode,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Transition between operational modes.
        
        Args:
            from_mode: The current mode
            to_mode: The target mode
            reason: Optional reason for the transition
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        # Validate that from_mode matches current mode
        if from_mode != self._current_mode:
            error_msg = (
                f"Cannot transition from {from_mode.value}: "
                f"current mode is {self._current_mode.value}"
            )
            record = ModeTransitionRecord(
                from_mode=from_mode,
                to_mode=to_mode,
                timestamp=time.time(),
                reason=reason,
                success=False,
                error_message=error_msg
            )
            self._transition_log.append(record)
            return False, error_msg

        # Validate transition is valid
        if not self._is_valid_transition(from_mode, to_mode):
            error_msg = f"Invalid transition from {from_mode.value} to {to_mode.value}"
            record = ModeTransitionRecord(
                from_mode=from_mode,
                to_mode=to_mode,
                timestamp=time.time(),
                reason=reason,
                success=False,
                error_message=error_msg
            )
            self._transition_log.append(record)
            return False, error_msg

        # Perform transition
        self._current_mode = to_mode
        record = ModeTransitionRecord(
            from_mode=from_mode,
            to_mode=to_mode,
            timestamp=time.time(),
            reason=reason,
            success=True
        )
        self._transition_log.append(record)
        return True, None

    def _is_valid_transition(
        self,
        from_mode: OperationalMode,
        to_mode: OperationalMode
    ) -> bool:
        """Validate that a mode transition is allowed.
        
        Valid transitions:
        - BOOTSTRAP -> DAY1
        - BOOTSTRAP -> DAY2
        - DAY1 -> DAY2
        - DAY1 -> BOOTSTRAP (for testing/reset)
        - DAY2 -> DAY1 (not allowed in production)
        - DAY2 -> BOOTSTRAP (not allowed in production)
        
        Args:
            from_mode: The current mode
            to_mode: The target mode
            
        Returns:
            bool: True if the transition is valid
        """
        # Cannot transition to the same mode
        if from_mode == to_mode:
            return False

        # Valid transitions
        valid_transitions = {
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY1),
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.BOOTSTRAP),
        }

        return (from_mode, to_mode) in valid_transitions

    def get_transition_history(self) -> List[ModeTransitionRecord]:
        """Get the complete transition history.
        
        Returns:
            List[ModeTransitionRecord]: Immutable copy of transition history
        """
        return list(self._transition_log)

    def get_violation_history(self) -> List[OperationViolation]:
        """Get the complete violation history.
        
        Returns:
            List[OperationViolation]: Immutable copy of violation history
        """
        return list(self._violation_log)

    def get_violations_in_mode(
        self,
        mode: OperationalMode
    ) -> List[OperationViolation]:
        """Get all violations that occurred in a specific mode.
        
        Args:
            mode: The operational mode to filter by
            
        Returns:
            List[OperationViolation]: Violations in the specified mode
        """
        return [v for v in self._violation_log if v.current_mode == mode]

    def get_violations_by_type(
        self,
        violation_type: str
    ) -> List[OperationViolation]:
        """Get all violations of a specific type.
        
        Args:
            violation_type: The type of violation to filter by
            
        Returns:
            List[OperationViolation]: Violations of the specified type
        """
        return [v for v in self._violation_log if v.violation_type == violation_type]
