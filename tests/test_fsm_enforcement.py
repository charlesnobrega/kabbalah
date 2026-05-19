"""Unit tests for FSM Enforcement Module."""

import pytest
import os
import time
from kabbalah.fsm_enforcement import (
    FSMEnforcementModule,
    OperationalMode,
    OperationType,
    Operation,
    ModeTransitionRecord,
    OperationViolation,
)


class TestFSMEnforcementModuleInitialization:
    """Tests for FSM module initialization."""

    def test_initialization_defaults_to_bootstrap(self, monkeypatch):
        """Test that module initializes to BOOTSTRAP mode by default."""
        monkeypatch.delenv("V5_RUNTIME_MODE", raising=False)
        module = FSMEnforcementModule()
        assert module.current_mode == OperationalMode.BOOTSTRAP

    def test_initialization_respects_environment_variable(self, monkeypatch):
        """Test that module respects V5_RUNTIME_MODE environment variable."""
        monkeypatch.setenv("V5_RUNTIME_MODE", "DAY2")
        module = FSMEnforcementModule()
        assert module.current_mode == OperationalMode.DAY2

    def test_initialization_case_insensitive(self, monkeypatch):
        """Test that mode detection is case-insensitive."""
        monkeypatch.setenv("V5_RUNTIME_MODE", "day1")
        module = FSMEnforcementModule()
        assert module.current_mode == OperationalMode.DAY1

    def test_initialization_invalid_mode_defaults_to_bootstrap(self, monkeypatch):
        """Test that invalid mode defaults to BOOTSTRAP."""
        monkeypatch.setenv("V5_RUNTIME_MODE", "INVALID_MODE")
        module = FSMEnforcementModule()
        assert module.current_mode == OperationalMode.BOOTSTRAP

    def test_initialization_empty_logs(self):
        """Test that logs are empty on initialization."""
        module = FSMEnforcementModule()
        assert module.transition_log == []
        assert module.violation_log == []


class TestCheckOperationAllowed:
    """Tests for check_operation_allowed method."""

    def test_bootstrap_operations_allowed_in_bootstrap_mode(self):
        """Test that bootstrap operations are allowed in BOOTSTRAP mode."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init_agent"
        )
        assert module.check_operation_allowed(operation, OperationalMode.BOOTSTRAP)

    def test_bootstrap_operations_allowed_in_day1_mode(self):
        """Test that bootstrap operations are allowed in DAY1 mode."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.MEMORY_RESET,
            operation_name="reset_memory"
        )
        assert module.check_operation_allowed(operation, OperationalMode.DAY1)

    def test_bootstrap_operations_blocked_in_day2_mode(self):
        """Test that bootstrap operations are blocked in DAY2 mode."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init_agent"
        )
        assert not module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_query_operations_allowed_in_all_modes(self):
        """Test that query operations are allowed in all modes."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.QUERY_OPERATION,
            operation_name="query_data"
        )
        assert module.check_operation_allowed(operation, OperationalMode.BOOTSTRAP)
        assert module.check_operation_allowed(operation, OperationalMode.DAY1)
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_read_operations_allowed_in_all_modes(self):
        """Test that read operations are allowed in all modes."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.READ_OPERATION,
            operation_name="read_file"
        )
        assert module.check_operation_allowed(operation, OperationalMode.BOOTSTRAP)
        assert module.check_operation_allowed(operation, OperationalMode.DAY1)
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_tool_execution_allowed_in_all_modes(self):
        """Test that tool execution is allowed in all modes."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.TOOL_EXECUTION,
            operation_name="execute_bash"
        )
        assert module.check_operation_allowed(operation, OperationalMode.BOOTSTRAP)
        assert module.check_operation_allowed(operation, OperationalMode.DAY1)
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_project_request_allowed_in_all_modes(self):
        """Test that project requests are allowed in all modes."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.PROJECT_REQUEST,
            operation_name="new_project"
        )
        assert module.check_operation_allowed(operation, OperationalMode.BOOTSTRAP)
        assert module.check_operation_allowed(operation, OperationalMode.DAY1)
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_uses_current_mode_when_not_specified(self, monkeypatch):
        """Test that check_operation_allowed uses current mode when not specified."""
        monkeypatch.setenv("V5_RUNTIME_MODE", "DAY2")
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init_agent"
        )
        assert not module.check_operation_allowed(operation)


class TestCheckOperationAllowedWithLogging:
    """Tests for check_operation_allowed_with_logging method."""

    def test_allowed_operation_returns_true_and_no_error(self):
        """Test that allowed operations return True and no error message."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.QUERY_OPERATION,
            operation_name="query_data"
        )
        is_allowed, error_msg = module.check_operation_allowed_with_logging(
            operation, OperationalMode.DAY2
        )
        assert is_allowed is True
        assert error_msg is None

    def test_blocked_operation_returns_false_and_error_message(self):
        """Test that blocked operations return False and error message."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init_agent"
        )
        is_allowed, error_msg = module.check_operation_allowed_with_logging(
            operation, OperationalMode.DAY2
        )
        assert is_allowed is False
        assert error_msg is not None
        assert "not allowed" in error_msg.lower()

    def test_violation_logged_for_blocked_operation(self):
        """Test that violations are logged for blocked operations."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.MEMORY_RESET,
            operation_name="reset_memory"
        )
        module.check_operation_allowed_with_logging(operation, OperationalMode.DAY2)
        
        violations = module.violation_log
        assert len(violations) == 1
        assert violations[0].operation == operation
        assert violations[0].current_mode == OperationalMode.DAY2
        assert violations[0].violation_type == "BOOTSTRAP_OPERATION_IN_DAY2"

    def test_multiple_violations_logged(self):
        """Test that multiple violations are logged."""
        module = FSMEnforcementModule()
        op1 = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init_agent"
        )
        op2 = Operation(
            operation_type=OperationType.MEMORY_RESET,
            operation_name="reset_memory"
        )
        
        module.check_operation_allowed_with_logging(op1, OperationalMode.DAY2)
        module.check_operation_allowed_with_logging(op2, OperationalMode.DAY2)
        
        assert len(module.violation_log) == 2


class TestModeTransition:
    """Tests for transition_mode method."""

    def test_valid_transition_bootstrap_to_day1(self):
        """Test valid transition from BOOTSTRAP to DAY1."""
        module = FSMEnforcementModule()
        success, error = module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.DAY1,
            reason="Initial deployment"
        )
        assert success is True
        assert error is None
        assert module.current_mode == OperationalMode.DAY1

    def test_valid_transition_bootstrap_to_day2(self):
        """Test valid transition from BOOTSTRAP to DAY2."""
        module = FSMEnforcementModule()
        success, error = module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.DAY2,
            reason="Direct to production"
        )
        assert success is True
        assert error is None
        assert module.current_mode == OperationalMode.DAY2

    def test_valid_transition_day1_to_day2(self):
        """Test valid transition from DAY1 to DAY2."""
        module = FSMEnforcementModule()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        success, error = module.transition_mode(
            OperationalMode.DAY1,
            OperationalMode.DAY2,
            reason="Production deployment"
        )
        assert success is True
        assert error is None
        assert module.current_mode == OperationalMode.DAY2

    def test_invalid_transition_same_mode(self):
        """Test that transitioning to same mode fails."""
        module = FSMEnforcementModule()
        success, error = module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.BOOTSTRAP
        )
        assert success is False
        assert error is not None

    def test_invalid_transition_day2_to_day1(self):
        """Test that transitioning from DAY2 to DAY1 fails."""
        module = FSMEnforcementModule()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY2)
        success, error = module.transition_mode(
            OperationalMode.DAY2,
            OperationalMode.DAY1
        )
        assert success is False
        assert error is not None

    def test_invalid_transition_day2_to_bootstrap(self):
        """Test that transitioning from DAY2 to BOOTSTRAP fails."""
        module = FSMEnforcementModule()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY2)
        success, error = module.transition_mode(
            OperationalMode.DAY2,
            OperationalMode.BOOTSTRAP
        )
        assert success is False
        assert error is not None

    def test_transition_fails_if_from_mode_mismatch(self):
        """Test that transition fails if from_mode doesn't match current mode."""
        module = FSMEnforcementModule()
        success, error = module.transition_mode(
            OperationalMode.DAY1,
            OperationalMode.DAY2
        )
        assert success is False
        assert error is not None
        assert module.current_mode == OperationalMode.BOOTSTRAP

    def test_transition_logged_on_success(self):
        """Test that successful transitions are logged."""
        module = FSMEnforcementModule()
        module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.DAY1,
            reason="Test transition"
        )
        
        log = module.transition_log
        assert len(log) == 1
        assert log[0].from_mode == OperationalMode.BOOTSTRAP
        assert log[0].to_mode == OperationalMode.DAY1
        assert log[0].success is True
        assert log[0].reason == "Test transition"

    def test_transition_logged_on_failure(self):
        """Test that failed transitions are logged."""
        module = FSMEnforcementModule()
        module.transition_mode(
            OperationalMode.DAY1,
            OperationalMode.DAY2
        )
        
        log = module.transition_log
        assert len(log) == 1
        assert log[0].success is False
        assert log[0].error_message is not None

    def test_transition_timestamp_recorded(self):
        """Test that transition timestamp is recorded."""
        module = FSMEnforcementModule()
        before = time.time()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        after = time.time()
        
        log = module.transition_log
        assert before <= log[0].timestamp <= after


class TestAuditLogs:
    """Tests for audit log functionality."""

    def test_transition_log_is_immutable(self):
        """Test that transition log returns a copy."""
        module = FSMEnforcementModule()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        
        log1 = module.transition_log
        log2 = module.transition_log
        
        # Should be equal but not the same object
        assert log1 == log2
        assert log1 is not log2

    def test_violation_log_is_immutable(self):
        """Test that violation log returns a copy."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init"
        )
        module.check_operation_allowed_with_logging(operation, OperationalMode.DAY2)
        
        log1 = module.violation_log
        log2 = module.violation_log
        
        # Should be equal but not the same object
        assert log1 == log2
        assert log1 is not log2

    def test_get_transition_history(self):
        """Test get_transition_history method."""
        module = FSMEnforcementModule()
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        history = module.get_transition_history()
        assert len(history) == 2
        assert history[0].to_mode == OperationalMode.DAY1
        assert history[1].to_mode == OperationalMode.DAY2

    def test_get_violation_history(self):
        """Test get_violation_history method."""
        module = FSMEnforcementModule()
        op1 = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init1"
        )
        op2 = Operation(
            operation_type=OperationType.MEMORY_RESET,
            operation_name="reset"
        )
        
        module.check_operation_allowed_with_logging(op1, OperationalMode.DAY2)
        module.check_operation_allowed_with_logging(op2, OperationalMode.DAY2)
        
        history = module.get_violation_history()
        assert len(history) == 2

    def test_get_violations_in_mode(self):
        """Test filtering violations by mode."""
        module = FSMEnforcementModule()
        op = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init"
        )
        
        module.check_operation_allowed_with_logging(op, OperationalMode.DAY2)
        module.check_operation_allowed_with_logging(op, OperationalMode.DAY1)
        
        day2_violations = module.get_violations_in_mode(OperationalMode.DAY2)
        day1_violations = module.get_violations_in_mode(OperationalMode.DAY1)
        
        assert len(day2_violations) == 1
        assert len(day1_violations) == 0

    def test_get_violations_by_type(self):
        """Test filtering violations by type."""
        module = FSMEnforcementModule()
        op1 = Operation(
            operation_type=OperationType.AGENT_INITIALIZATION,
            operation_name="init"
        )
        op2 = Operation(
            operation_type=OperationType.QUERY_OPERATION,
            operation_name="query"
        )
        
        module.check_operation_allowed_with_logging(op1, OperationalMode.DAY2)
        module.check_operation_allowed_with_logging(op2, OperationalMode.DAY2)
        
        bootstrap_violations = module.get_violations_by_type("BOOTSTRAP_OPERATION_IN_DAY2")
        assert len(bootstrap_violations) == 1


class TestOperationTypes:
    """Tests for different operation types."""

    def test_all_bootstrap_operations_blocked_in_day2(self):
        """Test that all bootstrap operations are blocked in DAY2."""
        module = FSMEnforcementModule()
        bootstrap_ops = [
            OperationType.BOOTSTRAP_OPERATION,
            OperationType.AGENT_INITIALIZATION,
            OperationType.MEMORY_RESET,
            OperationType.CONFIGURATION_CHANGE,
        ]
        
        for op_type in bootstrap_ops:
            operation = Operation(
                operation_type=op_type,
                operation_name=f"test_{op_type.value}"
            )
            assert not module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_all_allowed_operations_in_day2(self):
        """Test that allowed operations work in DAY2."""
        module = FSMEnforcementModule()
        allowed_ops = [
            OperationType.QUERY_OPERATION,
            OperationType.READ_OPERATION,
            OperationType.TOOL_EXECUTION,
            OperationType.PROJECT_REQUEST,
        ]
        
        for op_type in allowed_ops:
            operation = Operation(
                operation_type=op_type,
                operation_name=f"test_{op_type.value}"
            )
            assert module.check_operation_allowed(operation, OperationalMode.DAY2)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_operation_with_metadata(self):
        """Test that operations with metadata are handled correctly."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.QUERY_OPERATION,
            operation_name="query_with_metadata",
            metadata={"user_id": "123", "timestamp": 1234567890}
        )
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)

    def test_multiple_transitions_in_sequence(self):
        """Test multiple transitions in sequence."""
        module = FSMEnforcementModule()
        
        success1, _ = module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        success2, _ = module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        assert success1 is True
        assert success2 is True
        assert module.current_mode == OperationalMode.DAY2
        assert len(module.transition_log) == 2

    def test_many_violations_logged(self):
        """Test that many violations can be logged."""
        module = FSMEnforcementModule()
        
        for i in range(100):
            operation = Operation(
                operation_type=OperationType.AGENT_INITIALIZATION,
                operation_name=f"init_{i}"
            )
            module.check_operation_allowed_with_logging(operation, OperationalMode.DAY2)
        
        assert len(module.violation_log) == 100

    def test_operation_allowed_with_none_metadata(self):
        """Test that operations with None metadata are handled."""
        module = FSMEnforcementModule()
        operation = Operation(
            operation_type=OperationType.READ_OPERATION,
            operation_name="read_op",
            metadata={}
        )
        assert module.check_operation_allowed(operation, OperationalMode.DAY2)



# ============================================================================
# Property-Based Tests for Mode Transitions (Property 10)
# ============================================================================

from hypothesis import given, strategies as st, assume


class TestModeTransitionProperties:
    """Property-based tests for mode transitions.
    
    **Validates: Requirements 2, 10**
    
    Property 10: Mode transitions follow defined rules and are logged.
    
    This test suite verifies:
    - Valid mode transitions succeed
    - Valid transitions are logged with timestamp and reason
    - Invalid mode transitions fail
    - Failed transitions are logged
    - Transition chains work correctly (BOOTSTRAP → DAY1 → DAY2)
    - Invalid transitions are blocked (DAY2 → DAY1, DAY2 → BOOTSTRAP)
    """

    # Strategy for generating valid mode transitions
    valid_transition_strategy = st.sampled_from([
        (OperationalMode.BOOTSTRAP, OperationalMode.DAY1),
        (OperationalMode.BOOTSTRAP, OperationalMode.DAY2),
        (OperationalMode.DAY1, OperationalMode.DAY2),
        (OperationalMode.DAY1, OperationalMode.BOOTSTRAP),
    ])

    # Strategy for generating invalid mode transitions
    invalid_transition_strategy = st.sampled_from([
        (OperationalMode.BOOTSTRAP, OperationalMode.BOOTSTRAP),  # Same mode
        (OperationalMode.DAY1, OperationalMode.DAY1),  # Same mode
        (OperationalMode.DAY2, OperationalMode.DAY2),  # Same mode
        (OperationalMode.DAY2, OperationalMode.DAY1),  # Backward transition
        (OperationalMode.DAY2, OperationalMode.BOOTSTRAP),  # Backward transition
    ])

    # Strategy for generating optional reasons
    reason_strategy = st.one_of(
        st.none(),
        st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != "")
    )

    @given(
        from_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1]),
        to_mode=st.sampled_from([OperationalMode.DAY1, OperationalMode.DAY2]),
        reason=reason_strategy
    )
    def test_valid_transitions_succeed(self, from_mode, to_mode, reason):
        """Property: Valid mode transitions always succeed.
        
        Valid transitions are:
        - BOOTSTRAP → DAY1
        - BOOTSTRAP → DAY2
        - DAY1 → DAY2
        - DAY1 → BOOTSTRAP
        """
        # Skip invalid combinations
        if from_mode == to_mode:
            assume(False)
        if from_mode == OperationalMode.DAY2:
            assume(False)
        if from_mode == OperationalMode.BOOTSTRAP and to_mode == OperationalMode.BOOTSTRAP:
            assume(False)
        if from_mode == OperationalMode.DAY1 and to_mode == OperationalMode.DAY1:
            assume(False)

        module = FSMEnforcementModule()
        
        # Transition to from_mode first if needed
        if from_mode != OperationalMode.BOOTSTRAP:
            module.transition_mode(OperationalMode.BOOTSTRAP, from_mode)
        
        # Perform the transition
        success, error_msg = module.transition_mode(from_mode, to_mode, reason)
        
        # Valid transitions must succeed
        assert success is True, f"Valid transition {from_mode.value} → {to_mode.value} failed"
        assert error_msg is None
        assert module.current_mode == to_mode

    @given(
        from_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1, OperationalMode.DAY2]),
        to_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1, OperationalMode.DAY2]),
        reason=reason_strategy
    )
    def test_invalid_transitions_fail(self, from_mode, to_mode, reason):
        """Property: Invalid mode transitions always fail.
        
        Invalid transitions are:
        - Same mode → Same mode
        - DAY2 → DAY1
        - DAY2 → BOOTSTRAP
        """
        # Skip valid transitions
        valid_transitions = {
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY1),
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.BOOTSTRAP),
        }
        
        if (from_mode, to_mode) in valid_transitions:
            assume(False)

        module = FSMEnforcementModule()
        
        # Transition to from_mode first if needed
        if from_mode != OperationalMode.BOOTSTRAP:
            module.transition_mode(OperationalMode.BOOTSTRAP, from_mode)
            if from_mode == OperationalMode.DAY2:
                module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        # Perform the invalid transition
        success, error_msg = module.transition_mode(from_mode, to_mode, reason)
        
        # Invalid transitions must fail
        assert success is False, f"Invalid transition {from_mode.value} → {to_mode.value} should fail"
        assert error_msg is not None
        assert module.current_mode == from_mode  # Mode should not change

    @given(
        from_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1]),
        to_mode=st.sampled_from([OperationalMode.DAY1, OperationalMode.DAY2]),
        reason=reason_strategy
    )
    def test_valid_transitions_are_logged(self, from_mode, to_mode, reason):
        """Property: All valid transitions are logged with timestamp and reason.
        
        Each transition log entry must contain:
        - from_mode
        - to_mode
        - timestamp (non-zero)
        - reason (if provided)
        - success flag (True)
        """
        # Skip invalid combinations
        if from_mode == to_mode:
            assume(False)
        if from_mode == OperationalMode.DAY2:
            assume(False)

        module = FSMEnforcementModule()
        
        # Transition to from_mode first if needed
        if from_mode != OperationalMode.BOOTSTRAP:
            module.transition_mode(OperationalMode.BOOTSTRAP, from_mode)
        
        initial_log_size = len(module.transition_log)
        
        # Perform the transition
        success, _ = module.transition_mode(from_mode, to_mode, reason)
        
        assert success is True
        assert len(module.transition_log) == initial_log_size + 1
        
        # Verify the log entry
        log_entry = module.transition_log[-1]
        assert log_entry.from_mode == from_mode
        assert log_entry.to_mode == to_mode
        assert log_entry.timestamp > 0
        assert log_entry.reason == reason
        assert log_entry.success is True
        assert log_entry.error_message is None

    @given(
        from_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1, OperationalMode.DAY2]),
        to_mode=st.sampled_from([OperationalMode.BOOTSTRAP, OperationalMode.DAY1, OperationalMode.DAY2]),
        reason=reason_strategy
    )
    def test_invalid_transitions_are_logged(self, from_mode, to_mode, reason):
        """Property: All invalid transitions are logged with error message.
        
        Each failed transition log entry must contain:
        - from_mode
        - to_mode
        - timestamp (non-zero)
        - reason (if provided)
        - success flag (False)
        - error_message (non-empty)
        """
        # Skip valid transitions
        valid_transitions = {
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY1),
            (OperationalMode.BOOTSTRAP, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.DAY2),
            (OperationalMode.DAY1, OperationalMode.BOOTSTRAP),
        }
        
        if (from_mode, to_mode) in valid_transitions:
            assume(False)

        module = FSMEnforcementModule()
        
        # Transition to from_mode first if needed
        if from_mode != OperationalMode.BOOTSTRAP:
            module.transition_mode(OperationalMode.BOOTSTRAP, from_mode)
            if from_mode == OperationalMode.DAY2:
                module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        initial_log_size = len(module.transition_log)
        
        # Perform the invalid transition
        success, error_msg = module.transition_mode(from_mode, to_mode, reason)
        
        assert success is False
        assert len(module.transition_log) == initial_log_size + 1
        
        # Verify the log entry
        log_entry = module.transition_log[-1]
        assert log_entry.from_mode == from_mode
        assert log_entry.to_mode == to_mode
        assert log_entry.timestamp > 0
        assert log_entry.reason == reason
        assert log_entry.success is False
        assert log_entry.error_message is not None
        assert len(log_entry.error_message) > 0

    def test_transition_chain_bootstrap_to_day1_to_day2(self):
        """Property: Transition chain BOOTSTRAP → DAY1 → DAY2 succeeds.
        
        This tests the most common production transition path.
        """
        module = FSMEnforcementModule()
        
        # BOOTSTRAP → DAY1
        success1, _ = module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.DAY1,
            reason="Initial deployment"
        )
        assert success1 is True
        assert module.current_mode == OperationalMode.DAY1
        
        # DAY1 → DAY2
        success2, _ = module.transition_mode(
            OperationalMode.DAY1,
            OperationalMode.DAY2,
            reason="Production deployment"
        )
        assert success2 is True
        assert module.current_mode == OperationalMode.DAY2
        
        # Verify both transitions are logged
        assert len(module.transition_log) == 2
        assert module.transition_log[0].from_mode == OperationalMode.BOOTSTRAP
        assert module.transition_log[0].to_mode == OperationalMode.DAY1
        assert module.transition_log[1].from_mode == OperationalMode.DAY1
        assert module.transition_log[1].to_mode == OperationalMode.DAY2

    def test_invalid_transition_day2_to_day1_blocked(self):
        """Property: Invalid transition DAY2 → DAY1 is blocked.
        
        Once in production (DAY2), the system cannot transition back to DAY1.
        """
        module = FSMEnforcementModule()
        
        # Transition to DAY2
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        # Attempt invalid transition DAY2 → DAY1
        success, error_msg = module.transition_mode(
            OperationalMode.DAY2,
            OperationalMode.DAY1
        )
        
        assert success is False
        assert error_msg is not None
        assert module.current_mode == OperationalMode.DAY2

    def test_invalid_transition_day2_to_bootstrap_blocked(self):
        """Property: Invalid transition DAY2 → BOOTSTRAP is blocked.
        
        Once in production (DAY2), the system cannot transition back to BOOTSTRAP.
        """
        module = FSMEnforcementModule()
        
        # Transition to DAY2
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        # Attempt invalid transition DAY2 → BOOTSTRAP
        success, error_msg = module.transition_mode(
            OperationalMode.DAY2,
            OperationalMode.BOOTSTRAP
        )
        
        assert success is False
        assert error_msg is not None
        assert module.current_mode == OperationalMode.DAY2

    @given(
        transitions=st.lists(
            valid_transition_strategy,
            min_size=1,
            max_size=5
        )
    )
    def test_multiple_valid_transitions_all_logged(self, transitions):
        """Property: All transitions in a sequence are logged correctly.
        
        When multiple transitions occur, each one is logged with proper
        sequencing and all transitions succeed.
        """
        module = FSMEnforcementModule()
        
        # Build a valid sequence starting from BOOTSTRAP
        current_mode = OperationalMode.BOOTSTRAP
        valid_sequence = []
        
        for from_mode, to_mode in transitions:
            # Only add transitions that are valid from current mode
            if from_mode == current_mode:
                valid_sequence.append((from_mode, to_mode))
                current_mode = to_mode
        
        # Execute the sequence
        for from_mode, to_mode in valid_sequence:
            success, _ = module.transition_mode(from_mode, to_mode)
            assert success is True
        
        # Verify all transitions are logged
        assert len(module.transition_log) == len(valid_sequence)
        
        # Verify log entries are in order
        for i, (from_mode, to_mode) in enumerate(valid_sequence):
            log_entry = module.transition_log[i]
            assert log_entry.from_mode == from_mode
            assert log_entry.to_mode == to_mode
            assert log_entry.success is True

    @given(
        num_transitions=st.integers(min_value=1, max_value=10)
    )
    def test_transition_log_immutability(self, num_transitions):
        """Property: Transition log is immutable (returns copies).
        
        Modifying the returned log should not affect the internal log.
        """
        module = FSMEnforcementModule()
        
        # Perform some transitions
        for i in range(min(num_transitions, 3)):
            if i == 0:
                module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
            elif i == 1:
                module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
            elif i == 2:
                module.transition_mode(OperationalMode.DAY1, OperationalMode.BOOTSTRAP)
        
        # Get the log
        log1 = module.transition_log
        original_size = len(log1)
        
        # Try to modify the returned log
        if log1:
            log1.pop()
        
        # Get the log again
        log2 = module.transition_log
        
        # The internal log should be unchanged
        assert len(log2) == original_size

    @given(
        reason=reason_strategy
    )
    def test_transition_reason_preserved_in_log(self, reason):
        """Property: Transition reason is preserved in the log.
        
        If a reason is provided, it must be stored in the log entry.
        """
        module = FSMEnforcementModule()
        
        success, _ = module.transition_mode(
            OperationalMode.BOOTSTRAP,
            OperationalMode.DAY1,
            reason=reason
        )
        
        assert success is True
        log_entry = module.transition_log[0]
        assert log_entry.reason == reason

    def test_transition_timestamps_are_monotonic(self):
        """Property: Transition timestamps are monotonically increasing.
        
        Each transition should have a timestamp >= the previous one.
        """
        module = FSMEnforcementModule()
        
        # Perform multiple transitions
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.BOOTSTRAP)
        
        # Check timestamps are monotonic
        log = module.transition_log
        for i in range(1, len(log)):
            assert log[i].timestamp >= log[i-1].timestamp

    @given(
        num_invalid_attempts=st.integers(min_value=1, max_value=10)
    )
    def test_failed_transitions_do_not_change_mode(self, num_invalid_attempts):
        """Property: Failed transitions do not change the current mode.
        
        When a transition fails, the mode should remain unchanged.
        """
        module = FSMEnforcementModule()
        
        # Transition to DAY2
        module.transition_mode(OperationalMode.BOOTSTRAP, OperationalMode.DAY1)
        module.transition_mode(OperationalMode.DAY1, OperationalMode.DAY2)
        
        initial_mode = module.current_mode
        
        # Attempt multiple invalid transitions
        for _ in range(num_invalid_attempts):
            success, _ = module.transition_mode(
                OperationalMode.DAY2,
                OperationalMode.DAY1
            )
            assert success is False
            assert module.current_mode == initial_mode

    def test_transition_from_wrong_mode_fails(self):
        """Property: Transition from wrong mode fails.
        
        If the from_mode doesn't match current_mode, transition fails.
        """
        module = FSMEnforcementModule()
        
        # Try to transition from DAY1 when in BOOTSTRAP
        success, error_msg = module.transition_mode(
            OperationalMode.DAY1,
            OperationalMode.DAY2
        )
        
        assert success is False
        assert error_msg is not None
        assert "current mode is" in error_msg.lower()
        assert module.current_mode == OperationalMode.BOOTSTRAP
