"""Property-based tests for DAY2 enforcement (Property 8).

**Validates: Requirements 2.1.7 - Property 8**

Property 8: In DAY2 mode, bootstrap operations are always blocked.

Formulation:
FOR ALL operations op:
  IF V5_RUNTIME_MODE == "DAY2" AND op.type IN [bootstrap_operation]
  THEN op.status == BLOCKED AND violation_logged == true

This test suite uses hypothesis to generate random bootstrap operations
and verify that they are always blocked in DAY2 mode with violations logged.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from kabbalah.fsm_enforcement import (
    FSMEnforcementModule,
    OperationalMode,
    OperationType,
    Operation,
)


# Strategy for generating bootstrap operation types
bootstrap_operation_types = st.sampled_from([
    OperationType.BOOTSTRAP_OPERATION,
    OperationType.AGENT_INITIALIZATION,
    OperationType.MEMORY_RESET,
    OperationType.CONFIGURATION_CHANGE,
])

# Strategy for generating operation names
operation_names = st.text(
    alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Strategy for generating metadata dictionaries
metadata_strategy = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip()),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
    max_size=5
)

# Strategy for generating bootstrap operations
bootstrap_operations = st.builds(
    Operation,
    operation_type=bootstrap_operation_types,
    operation_name=operation_names,
    metadata=metadata_strategy,
)


class TestDAY2EnforcementProperty:
    """Property-based tests for DAY2 enforcement."""

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_all_bootstrap_operations_blocked_in_day2(self, operation):
        """Property: All bootstrap operations are blocked in DAY2 mode.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN op.status == BLOCKED
        """
        module = FSMEnforcementModule()
        
        # Check that operation is blocked in DAY2
        is_allowed = module.check_operation_allowed(
            operation,
            OperationalMode.DAY2
        )
        
        # Property: bootstrap operations must be blocked in DAY2
        assert not is_allowed, (
            f"Bootstrap operation {operation.operation_type.value} "
            f"should be blocked in DAY2 mode"
        )

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_all_bootstrap_operations_violations_logged_in_day2(self, operation):
        """Property: All bootstrap operation violations are logged in DAY2 mode.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "DAY2" AND op.type IN [bootstrap_operation]
          THEN violation_logged == true
        """
        module = FSMEnforcementModule()
        
        # Check operation with logging
        is_allowed, error_msg = module.check_operation_allowed_with_logging(
            operation,
            OperationalMode.DAY2
        )
        
        # Property: operation must be blocked
        assert not is_allowed, (
            f"Bootstrap operation {operation.operation_type.value} "
            f"should be blocked in DAY2 mode"
        )
        
        # Property: error message must be provided
        assert error_msg is not None, (
            f"Error message should be provided for blocked operation"
        )
        
        # Property: violation must be logged
        violations = module.violation_log
        assert len(violations) > 0, (
            f"At least one violation should be logged for blocked operation"
        )
        
        # Property: violation must reference the operation
        last_violation = violations[-1]
        assert last_violation.operation == operation, (
            f"Violation should reference the blocked operation"
        )
        
        # Property: violation must be in DAY2 mode
        assert last_violation.current_mode == OperationalMode.DAY2, (
            f"Violation should be recorded in DAY2 mode"
        )
        
        # Property: violation type must be BOOTSTRAP_OPERATION_IN_DAY2
        assert last_violation.violation_type == "BOOTSTRAP_OPERATION_IN_DAY2", (
            f"Violation type should be BOOTSTRAP_OPERATION_IN_DAY2"
        )

    @given(
        bootstrap_operations,
        st.lists(bootstrap_operations, min_size=1, max_size=10)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_multiple_bootstrap_operations_all_blocked_in_day2(
        self,
        first_operation,
        remaining_operations
    ):
        """Property: Multiple bootstrap operations are all blocked in DAY2.
        
        FOR ALL sequences of bootstrap operations ops:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN ALL ops are BLOCKED
        """
        module = FSMEnforcementModule()
        all_operations = [first_operation] + remaining_operations
        
        # Check all operations using logging version to capture violations
        for operation in all_operations:
            is_allowed, error_msg = module.check_operation_allowed_with_logging(
                operation,
                OperationalMode.DAY2
            )
            
            # Property: each operation must be blocked
            assert not is_allowed, (
                f"Bootstrap operation {operation.operation_type.value} "
                f"should be blocked in DAY2 mode"
            )
        
        # Property: all violations must be logged
        violations = module.violation_log
        assert len(violations) == len(all_operations), (
            f"All {len(all_operations)} operations should have violations logged"
        )

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_bootstrap_operations_allowed_in_bootstrap_mode(self, operation):
        """Property: Bootstrap operations are allowed in BOOTSTRAP mode.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "BOOTSTRAP"
          THEN op.status == ALLOWED
        """
        module = FSMEnforcementModule()
        
        # Check that operation is allowed in BOOTSTRAP
        is_allowed = module.check_operation_allowed(
            operation,
            OperationalMode.BOOTSTRAP
        )
        
        # Property: bootstrap operations must be allowed in BOOTSTRAP mode
        assert is_allowed, (
            f"Bootstrap operation {operation.operation_type.value} "
            f"should be allowed in BOOTSTRAP mode"
        )

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_bootstrap_operations_allowed_in_day1_mode(self, operation):
        """Property: Bootstrap operations are allowed in DAY1 mode.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "DAY1"
          THEN op.status == ALLOWED
        """
        module = FSMEnforcementModule()
        
        # Check that operation is allowed in DAY1
        is_allowed = module.check_operation_allowed(
            operation,
            OperationalMode.DAY1
        )
        
        # Property: bootstrap operations must be allowed in DAY1 mode
        assert is_allowed, (
            f"Bootstrap operation {operation.operation_type.value} "
            f"should be allowed in DAY1 mode"
        )

    @given(
        bootstrap_operations,
        st.lists(bootstrap_operations, min_size=1, max_size=5)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_violation_log_consistency_across_multiple_operations(
        self,
        first_operation,
        remaining_operations
    ):
        """Property: Violation log is consistent across multiple operations.
        
        FOR ALL sequences of bootstrap operations ops:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN violation_log contains exactly len(ops) violations
               AND each violation references the corresponding operation
        """
        module = FSMEnforcementModule()
        all_operations = [first_operation] + remaining_operations
        
        # Check all operations with logging
        for operation in all_operations:
            module.check_operation_allowed_with_logging(
                operation,
                OperationalMode.DAY2
            )
        
        # Property: violation log must contain all violations
        violations = module.violation_log
        assert len(violations) == len(all_operations), (
            f"Violation log should contain {len(all_operations)} violations"
        )
        
        # Property: each violation must reference the corresponding operation
        for i, operation in enumerate(all_operations):
            assert violations[i].operation == operation, (
                f"Violation {i} should reference operation {i}"
            )
            assert violations[i].current_mode == OperationalMode.DAY2, (
                f"Violation {i} should be in DAY2 mode"
            )

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_violation_metadata_preserved_in_day2(self, operation):
        """Property: Operation metadata is preserved in violation records.
        
        FOR ALL bootstrap operations op with metadata:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN violation.operation.metadata == op.metadata
        """
        module = FSMEnforcementModule()
        
        # Check operation with logging
        module.check_operation_allowed_with_logging(
            operation,
            OperationalMode.DAY2
        )
        
        # Property: metadata must be preserved in violation
        violations = module.violation_log
        assert len(violations) > 0, "Violation should be logged"
        
        last_violation = violations[-1]
        assert last_violation.operation.metadata == operation.metadata, (
            f"Operation metadata should be preserved in violation"
        )

    @given(
        st.lists(bootstrap_operations, min_size=1, max_size=20)
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_all_bootstrap_operation_types_blocked_in_day2(self, operations):
        """Property: All types of bootstrap operations are blocked in DAY2.
        
        FOR ALL bootstrap operation types:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN operation_type is BLOCKED
        """
        module = FSMEnforcementModule()
        
        # Collect all operation types that were tested
        tested_types = set()
        
        for operation in operations:
            is_allowed = module.check_operation_allowed(
                operation,
                OperationalMode.DAY2
            )
            
            # Property: operation must be blocked
            assert not is_allowed, (
                f"Bootstrap operation {operation.operation_type.value} "
                f"should be blocked in DAY2 mode"
            )
            
            tested_types.add(operation.operation_type)
        
        # Property: all tested types should be bootstrap operations
        for op_type in tested_types:
            assert op_type in [
                OperationType.BOOTSTRAP_OPERATION,
                OperationType.AGENT_INITIALIZATION,
                OperationType.MEMORY_RESET,
                OperationType.CONFIGURATION_CHANGE,
            ], f"Operation type {op_type} should be a bootstrap operation"

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_day2_blocking_is_deterministic(self, operation):
        """Property: DAY2 blocking behavior is deterministic.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN check_operation_allowed(op) always returns False
        """
        module = FSMEnforcementModule()
        
        # Check operation multiple times
        results = [
            module.check_operation_allowed(operation, OperationalMode.DAY2)
            for _ in range(5)
        ]
        
        # Property: all results must be False
        assert all(result is False for result in results), (
            f"DAY2 blocking behavior should be deterministic"
        )
        
        # Property: all results must be identical
        assert len(set(results)) == 1, (
            f"All checks should return the same result"
        )

    @given(bootstrap_operations)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_violation_timestamp_recorded_in_day2(self, operation):
        """Property: Violation timestamp is recorded for DAY2 violations.
        
        FOR ALL bootstrap operations op:
          IF V5_RUNTIME_MODE == "DAY2"
          THEN violation.timestamp is recorded
        """
        import time
        
        module = FSMEnforcementModule()
        
        before = time.time()
        module.check_operation_allowed_with_logging(
            operation,
            OperationalMode.DAY2
        )
        after = time.time()
        
        # Property: violation must be logged with timestamp
        violations = module.violation_log
        assert len(violations) > 0, "Violation should be logged"
        
        last_violation = violations[-1]
        assert last_violation.timestamp is not None, (
            f"Violation timestamp should be recorded"
        )
        
        # Property: timestamp should be within the recorded time range
        assert before <= last_violation.timestamp <= after, (
            f"Violation timestamp should be within the recorded time range"
        )
