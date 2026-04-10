"""Property-based tests for Contract Enforcement Module.

**Validates: Requirements 2.3.7, 2.3.8, 2.3.9**

Property 15: Precondition validation always rejects invalid inputs.
Property 16: Postcondition validation always rejects invalid outputs.
Property 17: Contract violations are always logged with full context.

This test suite uses hypothesis to generate random operations, inputs,
and outputs to verify that contracts are enforced consistently.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from kabbalah.contract_enforcement import (
    ContractEnforcementModule,
    OperationContract,
    ContractViolation,
)


# Strategy for generating operation names
operation_names = st.text(
    alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())

# Strategy for generating trace IDs (run_id:branch_id:leaf_id)
trace_ids = st.builds(
    lambda r, b, l: f"run_{r}:branch_{b}:leaf_{l}",
    r=st.integers(min_value=1, max_value=1000),
    b=st.integers(min_value=1, max_value=100),
    l=st.integers(min_value=1, max_value=100),
)

# Strategy for generating input dictionaries
input_dicts = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
        min_size=1,
        max_size=30
    ).filter(lambda x: x.strip()),
    values=st.one_of(
        st.integers(),
        st.text(max_size=50),
        st.booleans(),
        st.none(),
    ),
    max_size=5
)

# Strategy for generating output dictionaries
output_dicts = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
        min_size=1,
        max_size=30
    ).filter(lambda x: x.strip()),
    values=st.one_of(
        st.integers(),
        st.text(max_size=50),
        st.booleans(),
        st.none(),
    ),
    max_size=5
)


class TestPreconditionValidationProperty:
    """Property-based tests for precondition validation (Property 15).
    
    **Validates: Requirements 2.3.7**
    
    Property 15: Precondition validation always rejects invalid inputs.
    
    Formulation:
    FOR ALL operations op, inputs inputs:
      IF precondition(inputs) == false
      THEN validate_preconditions(op, inputs) == false
    """

    @given(operation_names, input_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_precondition_rejects_invalid_inputs(self, op_name, inputs, trace_id):
        """Property: Invalid inputs are always rejected by preconditions.
        
        FOR ALL inputs:
          IF inputs["value"] < 0
          THEN validate_preconditions returns False
        """
        module = ContractEnforcementModule()
        
        # Define a precondition that rejects negative values
        def precond_positive_value(inputs):
            if "value" in inputs and inputs["value"] < 0:
                return False, "value must be non-negative"
            return True, None
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[precond_positive_value],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # Test with negative value
        test_inputs = dict(inputs)
        test_inputs["value"] = -42
        
        is_valid, error = module.validate_preconditions(op_name, test_inputs, trace_id)
        
        # Property: negative values must be rejected
        assert is_valid is False
        assert error == "value must be non-negative"

    @given(operation_names, input_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_precondition_accepts_valid_inputs(self, op_name, inputs, trace_id):
        """Property: Valid inputs are always accepted by preconditions.
        
        FOR ALL inputs:
          IF inputs["value"] >= 0
          THEN validate_preconditions returns True
        """
        module = ContractEnforcementModule()
        
        # Define a precondition that accepts non-negative values
        def precond_positive_value(inputs):
            if "value" in inputs and inputs["value"] < 0:
                return False, "value must be non-negative"
            return True, None
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[precond_positive_value],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # Test with non-negative value
        test_inputs = dict(inputs)
        test_inputs["value"] = 42
        
        is_valid, error = module.validate_preconditions(op_name, test_inputs, trace_id)
        
        # Property: non-negative values must be accepted
        assert is_valid is True
        assert error is None

    @given(operation_names, input_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_multiple_preconditions_all_enforced(self, op_name, inputs, trace_id):
        """Property: All preconditions are enforced.
        
        FOR ALL preconditions:
          IF any precondition fails
          THEN validate_preconditions returns False
        """
        module = ContractEnforcementModule()
        
        # Define multiple preconditions
        def precond1(inputs):
            if "value" in inputs and inputs["value"] < 0:
                return False, "value must be non-negative"
            return True, None
        
        def precond2(inputs):
            if "name" in inputs and len(inputs["name"]) == 0:
                return False, "name must not be empty"
            return True, None
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[precond1, precond2],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # Test with invalid value (fails precond1)
        test_inputs = dict(inputs)
        test_inputs["value"] = -42
        test_inputs["name"] = "valid"
        
        is_valid, error = module.validate_preconditions(op_name, test_inputs, trace_id)
        
        # Property: first failing precondition causes rejection
        assert is_valid is False


class TestPostconditionValidationProperty:
    """Property-based tests for postcondition validation (Property 16).
    
    **Validates: Requirements 2.3.8**
    
    Property 16: Postcondition validation always rejects invalid outputs.
    
    Formulation:
    FOR ALL operations op, outputs outputs:
      IF postcondition(outputs) == false
      THEN validate_postconditions(op, outputs) == false
    """

    @given(operation_names, output_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_postcondition_rejects_invalid_outputs(self, op_name, outputs, trace_id):
        """Property: Invalid outputs are always rejected by postconditions.
        
        FOR ALL outputs:
          IF outputs["result"] < 0
          THEN validate_postconditions returns False
        """
        module = ContractEnforcementModule()
        
        # Define a postcondition that rejects negative results
        def postcond_positive_result(outputs):
            if "result" in outputs and outputs["result"] < 0:
                return False, "result must be non-negative"
            return True, None
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[],
            postconditions=[postcond_positive_result],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # Test with negative result
        test_outputs = dict(outputs)
        test_outputs["result"] = -42
        
        is_valid, error = module.validate_postconditions(op_name, test_outputs, trace_id)
        
        # Property: negative results must be rejected
        assert is_valid is False
        assert error == "result must be non-negative"

    @given(operation_names, output_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_postcondition_accepts_valid_outputs(self, op_name, outputs, trace_id):
        """Property: Valid outputs are always accepted by postconditions.
        
        FOR ALL outputs:
          IF outputs["result"] >= 0
          THEN validate_postconditions returns True
        """
        module = ContractEnforcementModule()
        
        # Define a postcondition that accepts non-negative results
        def postcond_positive_result(outputs):
            if "result" in outputs and outputs["result"] < 0:
                return False, "result must be non-negative"
            return True, None
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[],
            postconditions=[postcond_positive_result],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # Test with non-negative result
        test_outputs = dict(outputs)
        test_outputs["result"] = 42
        
        is_valid, error = module.validate_postconditions(op_name, test_outputs, trace_id)
        
        # Property: non-negative results must be accepted
        assert is_valid is True
        assert error is None


class TestViolationLoggingProperty:
    """Property-based tests for violation logging (Property 17).
    
    **Validates: Requirements 2.3.9**
    
    Property 17: Contract violations are always logged with full context.
    
    Formulation:
    FOR ALL violations:
      violation.trace_id is set AND
      violation.operation_name is set AND
      violation.inputs is set AND
      violation.error_message is set
    """

    @given(operation_names, input_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_precondition_violations_logged_with_context(self, op_name, inputs, trace_id):
        """Property: Precondition violations are logged with full context.
        
        FOR ALL precondition violations:
          violation.trace_id == trace_id AND
          violation.operation_name == op_name AND
          violation.inputs == inputs AND
          violation.error_message is not None
        """
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions(op_name, inputs, trace_id)
        
        # Property: violation must be logged with full context
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        
        assert violation.trace_id == trace_id
        assert violation.operation_name == op_name
        assert violation.inputs == inputs
        assert violation.error_message is not None
        assert violation.violation_type == "precondition"

    @given(operation_names, output_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_postcondition_violations_logged_with_context(self, op_name, outputs, trace_id):
        """Property: Postcondition violations are logged with full context.
        
        FOR ALL postcondition violations:
          violation.trace_id == trace_id AND
          violation.operation_name == op_name AND
          violation.outputs == outputs AND
          violation.error_message is not None
        """
        module = ContractEnforcementModule()
        
        def postcond(outputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[],
            postconditions=[postcond],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_postconditions(op_name, outputs, trace_id)
        
        # Property: violation must be logged with full context
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        
        assert violation.trace_id == trace_id
        assert violation.operation_name == op_name
        assert violation.outputs == outputs
        assert violation.error_message is not None
        assert violation.violation_type == "postcondition"

    @given(operation_names, input_dicts, output_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_parser_violations_logged_with_context(self, op_name, inputs, outputs, trace_id):
        """Property: Parser violations are logged with full context.
        
        FOR ALL parser violations:
          violation.trace_id == trace_id AND
          violation.operation_name == op_name AND
          violation.outputs == outputs AND
          violation.error_message is not None
        """
        module = ContractEnforcementModule()
        
        def parser(outputs):
            return False, "parser error"
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[],
            postconditions=[],
            output_parser=parser
        )
        
        module.register_contract(contract)
        
        module.validate_output_parser(op_name, outputs, trace_id, inputs)
        
        # Property: violation must be logged with full context
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        
        assert violation.trace_id == trace_id
        assert violation.operation_name == op_name
        assert violation.outputs == outputs
        assert violation.error_message is not None
        assert violation.violation_type == "parser"

    @given(st.lists(operation_names, min_size=1, max_size=10, unique=True))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_multiple_violations_all_logged(self, op_names):
        """Property: All violations are logged separately.
        
        FOR ALL violations:
          len(violation_log) == number of violations
        """
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        # Register contracts for all operations
        for op_name in op_names:
            contract = OperationContract(
                operation_name=op_name,
                preconditions=[precond],
                postconditions=[],
                output_parser=None
            )
            module.register_contract(contract)
        
        # Generate violations for each operation
        for i, op_name in enumerate(op_names):
            module.validate_preconditions(
                op_name,
                {"index": i},
                f"run_001:branch_001:leaf_{i:03d}"
            )
        
        # Property: all violations must be logged
        assert len(module.violation_log) == len(op_names)
        
        # Verify each violation has unique trace_id
        trace_ids = [v.trace_id for v in module.violation_log]
        assert len(set(trace_ids)) == len(op_names)

    @given(operation_names, input_dicts, trace_ids)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_violation_has_timestamp(self, op_name, inputs, trace_id):
        """Property: All violations have timestamps.
        
        FOR ALL violations:
          violation.timestamp is set AND
          violation.timestamp > 0
        """
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name=op_name,
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions(op_name, inputs, trace_id)
        
        # Property: violation must have timestamp
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        
        assert violation.timestamp > 0
        assert isinstance(violation.timestamp, float)
