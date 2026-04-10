"""Unit tests for Contract Enforcement Module."""

import pytest
from datetime import datetime
from kabbalah.contract_enforcement import (
    ContractEnforcementModule,
    OperationContract,
    ContractViolation,
    ParserValidationResult
)


class TestContractEnforcementModuleInitialization:
    """Test initialization of ContractEnforcementModule."""

    def test_initialization_creates_empty_violation_log(self):
        """Test that initialization creates empty violation log."""
        module = ContractEnforcementModule()
        assert module.violation_log == []

    def test_initialization_creates_empty_contracts(self):
        """Test that initialization creates empty contracts registry."""
        module = ContractEnforcementModule()
        assert module._contracts == {}

    def test_violation_log_is_immutable(self):
        """Test that violation_log property returns immutable copy."""
        module = ContractEnforcementModule()
        log1 = module.violation_log
        log2 = module.violation_log
        assert log1 is not log2  # Different objects
        assert log1 == log2  # Same content


class TestRegisterContract:
    """Test contract registration."""

    def test_register_contract_stores_contract(self):
        """Test that registering a contract stores it."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return True, None
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        assert "test_op" in module._contracts
        assert module._contracts["test_op"] == contract

    def test_register_multiple_contracts(self):
        """Test registering multiple contracts."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return True, None
        
        contract1 = OperationContract(
            operation_name="op1",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        contract2 = OperationContract(
            operation_name="op2",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract1)
        module.register_contract(contract2)
        
        assert len(module._contracts) == 2
        assert "op1" in module._contracts
        assert "op2" in module._contracts


class TestValidatePreconditions:
    """Test precondition validation."""

    def test_precondition_passes_when_valid(self):
        """Test that valid precondition passes."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            if "value" in inputs and inputs["value"] > 0:
                return True, None
            return False, "value must be positive"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_preconditions(
            "test_op",
            {"value": 5},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is True
        assert error is None

    def test_precondition_fails_when_invalid(self):
        """Test that invalid precondition fails."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            if "value" in inputs and inputs["value"] > 0:
                return True, None
            return False, "value must be positive"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_preconditions(
            "test_op",
            {"value": -5},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is False
        assert error == "value must be positive"

    def test_precondition_violation_logged(self):
        """Test that precondition violation is logged."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions(
            "test_op",
            {"value": -5},
            "run_001:branch_001:leaf_001"
        )
        
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        assert violation.violation_type == "precondition"
        assert violation.operation_name == "test_op"
        assert violation.trace_id == "run_001:branch_001:leaf_001"

    def test_multiple_preconditions_all_checked(self):
        """Test that all preconditions are checked."""
        module = ContractEnforcementModule()
        
        def precond1(inputs):
            if "value" in inputs and inputs["value"] > 0:
                return True, None
            return False, "value must be positive"
        
        def precond2(inputs):
            if "name" in inputs and len(inputs["name"]) > 0:
                return True, None
            return False, "name must not be empty"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond1, precond2],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        # First precondition fails
        is_valid, error = module.validate_preconditions(
            "test_op",
            {"value": -5, "name": "test"},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is False
        assert error == "value must be positive"

    def test_precondition_with_no_contract_returns_true(self):
        """Test that operation with no contract passes."""
        module = ContractEnforcementModule()
        
        is_valid, error = module.validate_preconditions(
            "unknown_op",
            {"value": -5},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is True
        assert error is None


class TestValidatePostconditions:
    """Test postcondition validation."""

    def test_postcondition_passes_when_valid(self):
        """Test that valid postcondition passes."""
        module = ContractEnforcementModule()
        
        def postcond(outputs):
            if "result" in outputs and outputs["result"] > 0:
                return True, None
            return False, "result must be positive"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[postcond],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_postconditions(
            "test_op",
            {"result": 10},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is True
        assert error is None

    def test_postcondition_fails_when_invalid(self):
        """Test that invalid postcondition fails."""
        module = ContractEnforcementModule()
        
        def postcond(outputs):
            if "result" in outputs and outputs["result"] > 0:
                return True, None
            return False, "result must be positive"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[postcond],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_postconditions(
            "test_op",
            {"result": -10},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is False
        assert error == "result must be positive"

    def test_postcondition_violation_logged(self):
        """Test that postcondition violation is logged."""
        module = ContractEnforcementModule()
        
        def postcond(outputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[postcond],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_postconditions(
            "test_op",
            {"result": 10},
            "run_001:branch_001:leaf_001"
        )
        
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        assert violation.violation_type == "postcondition"
        assert violation.operation_name == "test_op"
        assert violation.outputs == {"result": 10}

    def test_postcondition_with_no_contract_returns_true(self):
        """Test that operation with no contract passes."""
        module = ContractEnforcementModule()
        
        is_valid, error = module.validate_postconditions(
            "unknown_op",
            {"result": 10},
            "run_001:branch_001:leaf_001"
        )
        
        assert is_valid is True
        assert error is None


class TestValidateOutputParser:
    """Test output parser validation."""

    def test_parser_passes_when_valid(self):
        """Test that valid parser passes."""
        module = ContractEnforcementModule()
        
        def parser(outputs):
            if "data" in outputs and isinstance(outputs["data"], dict):
                return True, None
            return False, "data must be a dict"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[],
            output_parser=parser
        )
        
        module.register_contract(contract)
        
        result = module.validate_output_parser(
            "test_op",
            {"data": {"key": "value"}},
            "run_001:branch_001:leaf_001"
        )
        
        assert result.is_valid is True
        assert result.error_message is None
        assert result.parsed_output == {"data": {"key": "value"}}

    def test_parser_fails_when_invalid(self):
        """Test that invalid parser fails."""
        module = ContractEnforcementModule()
        
        def parser(outputs):
            if "data" in outputs and isinstance(outputs["data"], dict):
                return True, None
            return False, "data must be a dict"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[],
            output_parser=parser
        )
        
        module.register_contract(contract)
        
        result = module.validate_output_parser(
            "test_op",
            {"data": "not a dict"},
            "run_001:branch_001:leaf_001"
        )
        
        assert result.is_valid is False
        assert result.error_message == "data must be a dict"
        assert result.parsed_output is None

    def test_parser_violation_logged(self):
        """Test that parser violation is logged."""
        module = ContractEnforcementModule()
        
        def parser(outputs):
            return False, "parser error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[],
            output_parser=parser
        )
        
        module.register_contract(contract)
        
        module.validate_output_parser(
            "test_op",
            {"data": "test"},
            "run_001:branch_001:leaf_001"
        )
        
        assert len(module.violation_log) == 1
        violation = module.violation_log[0]
        assert violation.violation_type == "parser"

    def test_parser_with_no_contract_returns_valid(self):
        """Test that operation with no contract passes."""
        module = ContractEnforcementModule()
        
        result = module.validate_output_parser(
            "unknown_op",
            {"data": "test"},
            "run_001:branch_001:leaf_001"
        )
        
        assert result.is_valid is True
        assert result.error_message is None

    def test_parser_with_no_parser_defined_returns_valid(self):
        """Test that operation with no parser defined passes."""
        module = ContractEnforcementModule()
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        result = module.validate_output_parser(
            "test_op",
            {"data": "test"},
            "run_001:branch_001:leaf_001"
        )
        
        assert result.is_valid is True
        assert result.error_message is None


class TestContractViolationLogging:
    """Test contract violation logging."""

    def test_violation_includes_full_context(self):
        """Test that violation includes full context."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        inputs = {"value": 5}
        trace_id = "run_001:branch_001:leaf_001"
        
        module.validate_preconditions("test_op", inputs, trace_id)
        
        violation = module.violation_log[0]
        assert violation.operation_name == "test_op"
        assert violation.violation_type == "precondition"
        assert violation.trace_id == trace_id
        assert violation.inputs == inputs
        assert violation.error_message == "test error"

    def test_violation_has_timestamp(self):
        """Test that violation has timestamp."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        before = datetime.now().timestamp()
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        after = datetime.now().timestamp()
        
        violation = module.violation_log[0]
        assert before <= violation.timestamp <= after

    def test_multiple_violations_logged_separately(self):
        """Test that multiple violations are logged separately."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions("test_op", {"a": 1}, "run_001:branch_001:leaf_001")
        module.validate_preconditions("test_op", {"b": 2}, "run_001:branch_001:leaf_002")
        
        assert len(module.violation_log) == 2
        assert module.violation_log[0].inputs == {"a": 1}
        assert module.violation_log[1].inputs == {"b": 2}


class TestViolationQueries:
    """Test violation query methods."""

    def test_get_violation_history(self):
        """Test getting violation history."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_002")
        
        history = module.get_violation_history()
        assert len(history) == 2

    def test_get_violations_by_trace_id(self):
        """Test getting violations by trace_id."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_002")
        
        violations = module.get_violations_by_trace_id("run_001:branch_001:leaf_001")
        assert len(violations) == 1
        assert violations[0].trace_id == "run_001:branch_001:leaf_001"

    def test_get_violations_by_operation(self):
        """Test getting violations by operation."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract1 = OperationContract(
            operation_name="op1",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        contract2 = OperationContract(
            operation_name="op2",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract1)
        module.register_contract(contract2)
        
        module.validate_preconditions("op1", {}, "run_001:branch_001:leaf_001")
        module.validate_preconditions("op2", {}, "run_001:branch_001:leaf_002")
        
        violations = module.get_violations_by_operation("op1")
        assert len(violations) == 1
        assert violations[0].operation_name == "op1"

    def test_get_violations_by_type(self):
        """Test getting violations by type."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        def postcond(outputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[postcond],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        module.validate_postconditions("test_op", {}, "run_001:branch_001:leaf_002")
        
        precond_violations = module.get_violations_by_type("precondition")
        postcond_violations = module.get_violations_by_type("postcondition")
        
        assert len(precond_violations) == 1
        assert len(postcond_violations) == 1


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_inputs_and_outputs(self):
        """Test with empty inputs and outputs."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return len(inputs) == 0, "inputs must be empty"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        assert is_valid is True

    def test_complex_nested_inputs(self):
        """Test with complex nested inputs."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            if "nested" in inputs and "deep" in inputs["nested"]:
                return True, None
            return False, "nested.deep required"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        inputs = {"nested": {"deep": {"value": 42}}}
        is_valid, error = module.validate_preconditions("test_op", inputs, "run_001:branch_001:leaf_001")
        assert is_valid is True

    def test_violation_with_none_error_message(self):
        """Test violation with None error message."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, None
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        is_valid, error = module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        assert is_valid is False
        assert error is None
        
        violation = module.violation_log[0]
        assert violation.error_message == "Precondition failed"

    def test_clear_violation_log(self):
        """Test clearing violation log."""
        module = ContractEnforcementModule()
        
        def precond(inputs):
            return False, "test error"
        
        contract = OperationContract(
            operation_name="test_op",
            preconditions=[precond],
            postconditions=[],
            output_parser=None
        )
        
        module.register_contract(contract)
        
        module.validate_preconditions("test_op", {}, "run_001:branch_001:leaf_001")
        assert len(module.violation_log) == 1
        
        module.clear_violation_log()
        assert len(module.violation_log) == 0
