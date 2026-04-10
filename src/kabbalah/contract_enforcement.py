"""Contract Enforcement Module for Kabbalah orchestration system.

This module enforces pre/post-conditions on all operations, validates output
format and structure, and logs contract violations with full context.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
import json
import logging


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ContractViolation:
    """Record of a contract violation."""
    violation_id: str
    operation_name: str
    violation_type: str  # "precondition", "postcondition", "parser"
    trace_id: str
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]]
    error_message: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationContract:
    """Contract specification for an operation."""
    operation_name: str
    preconditions: List[Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]]]
    postconditions: List[Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]]]
    output_parser: Optional[Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]]]
    description: str = ""


@dataclass
class ParserValidationResult:
    """Result of output parser validation."""
    is_valid: bool
    error_message: Optional[str]
    parsed_output: Optional[Dict[str, Any]]


class ContractEnforcementModule:
    """Enforces pre/post-conditions on all operations.
    
    This module validates preconditions before operation execution and
    postconditions after execution. It also validates output format and
    structure using configurable parsers. All contract violations are
    logged with full context including trace_id.
    """

    def __init__(self):
        """Initialize the Contract Enforcement Module."""
        self._violation_log: List[ContractViolation] = []
        self._contracts: Dict[str, OperationContract] = {}
        self._violation_counter = 0

    @property
    def violation_log(self) -> List[ContractViolation]:
        """Get immutable copy of violation log."""
        return list(self._violation_log)

    def register_contract(self, contract: OperationContract) -> None:
        """Register a contract for an operation.
        
        Args:
            contract: Operation contract specification
        """
        self._contracts[contract.operation_name] = contract

    def validate_preconditions(
        self,
        operation_name: str,
        inputs: Dict[str, Any],
        trace_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate preconditions before operation execution.
        
        Args:
            operation_name: Name of the operation
            inputs: Input parameters to validate
            trace_id: Hierarchical trace identifier
            
        Returns:
            (is_valid, error_message)
        """
        if operation_name not in self._contracts:
            # No contract registered, allow operation
            return True, None

        contract = self._contracts[operation_name]
        
        for precondition in contract.preconditions:
            is_valid, error_message = precondition(inputs)
            if not is_valid:
                # Log violation
                self._log_violation(
                    operation_name=operation_name,
                    violation_type="precondition",
                    trace_id=trace_id,
                    inputs=inputs,
                    outputs=None,
                    error_message=error_message or "Precondition failed"
                )
                return False, error_message

        return True, None

    def validate_postconditions(
        self,
        operation_name: str,
        outputs: Dict[str, Any],
        trace_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate postconditions after operation execution.
        
        Args:
            operation_name: Name of the operation
            outputs: Output results to validate
            trace_id: Hierarchical trace identifier
            inputs: Original inputs (for context)
            
        Returns:
            (is_valid, error_message)
        """
        if operation_name not in self._contracts:
            # No contract registered, allow operation
            return True, None

        contract = self._contracts[operation_name]
        
        for postcondition in contract.postconditions:
            is_valid, error_message = postcondition(outputs)
            if not is_valid:
                # Log violation
                self._log_violation(
                    operation_name=operation_name,
                    violation_type="postcondition",
                    trace_id=trace_id,
                    inputs=inputs or {},
                    outputs=outputs,
                    error_message=error_message or "Postcondition failed"
                )
                return False, error_message

        return True, None

    def validate_output_parser(
        self,
        operation_name: str,
        outputs: Dict[str, Any],
        trace_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> ParserValidationResult:
        """Validate output format and structure using parser.
        
        Args:
            operation_name: Name of the operation
            outputs: Output results to validate
            trace_id: Hierarchical trace identifier
            inputs: Original inputs (for context)
            
        Returns:
            ParserValidationResult with validation status and parsed output
        """
        if operation_name not in self._contracts:
            # No contract registered, allow operation
            return ParserValidationResult(
                is_valid=True,
                error_message=None,
                parsed_output=outputs
            )

        contract = self._contracts[operation_name]
        
        if contract.output_parser is None:
            # No parser defined, allow operation
            return ParserValidationResult(
                is_valid=True,
                error_message=None,
                parsed_output=outputs
            )

        is_valid, error_message = contract.output_parser(outputs)
        
        if not is_valid:
            # Log violation
            self._log_violation(
                operation_name=operation_name,
                violation_type="parser",
                trace_id=trace_id,
                inputs=inputs or {},
                outputs=outputs,
                error_message=error_message or "Parser validation failed"
            )
            return ParserValidationResult(
                is_valid=False,
                error_message=error_message,
                parsed_output=None
            )

        return ParserValidationResult(
            is_valid=True,
            error_message=None,
            parsed_output=outputs
        )

    def _log_violation(
        self,
        operation_name: str,
        violation_type: str,
        trace_id: str,
        inputs: Dict[str, Any],
        outputs: Optional[Dict[str, Any]],
        error_message: str
    ) -> None:
        """Log a contract violation with full context.
        
        Args:
            operation_name: Name of the operation
            violation_type: Type of violation (precondition, postcondition, parser)
            trace_id: Hierarchical trace identifier
            inputs: Input parameters
            outputs: Output results (if applicable)
            error_message: Error message
        """
        self._violation_counter += 1
        violation_id = f"violation_{self._violation_counter}"
        
        violation = ContractViolation(
            violation_id=violation_id,
            operation_name=operation_name,
            violation_type=violation_type,
            trace_id=trace_id,
            inputs=inputs,
            outputs=outputs,
            error_message=error_message,
            timestamp=datetime.now().timestamp(),
            context={
                "operation_name": operation_name,
                "violation_type": violation_type,
                "trace_id": trace_id
            }
        )
        
        self._violation_log.append(violation)
        
        # Log to logger
        logger.error(
            f"Contract violation: {violation_type} for operation {operation_name}",
            extra={
                "violation_id": violation_id,
                "trace_id": trace_id,
                "error_message": error_message,
                "inputs": inputs,
                "outputs": outputs
            }
        )

    def get_violation_history(self) -> List[ContractViolation]:
        """Get complete violation history.
        
        Returns:
            List of all contract violations
        """
        return list(self._violation_log)

    def get_violations_by_trace_id(self, trace_id: str) -> List[ContractViolation]:
        """Get violations for a specific trace_id.
        
        Args:
            trace_id: Hierarchical trace identifier
            
        Returns:
            List of violations for the trace_id
        """
        return [v for v in self._violation_log if v.trace_id == trace_id]

    def get_violations_by_operation(self, operation_name: str) -> List[ContractViolation]:
        """Get violations for a specific operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            List of violations for the operation
        """
        return [v for v in self._violation_log if v.operation_name == operation_name]

    def get_violations_by_type(self, violation_type: str) -> List[ContractViolation]:
        """Get violations of a specific type.
        
        Args:
            violation_type: Type of violation (precondition, postcondition, parser)
            
        Returns:
            List of violations of the type
        """
        return [v for v in self._violation_log if v.violation_type == violation_type]

    def clear_violation_log(self) -> None:
        """Clear the violation log (for testing purposes)."""
        self._violation_log.clear()
        self._violation_counter = 0
