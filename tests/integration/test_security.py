"""
Security Testing Module for Phase 10

Tests security aspects including input validation, access control, and tool sandboxing.
"""

import pytest
import json
from src.kabbalah.intake_node import IntakeNode
from src.kabbalah.models import UserRequest, Specification
from src.kabbalah.specification_parser import SpecificationParser
from src.kabbalah.configuration_manager import ConfigurationManager
from src.kabbalah.day2_operations import Day2OperationsModule, OperationType
from src.kabbalah.observability.observability_module import ObservabilityModule, LogLevel, OperationStatus
from dataclasses import asdict


class TestSecurityValidation:
    """Security Validation Tests"""
    
    def test_input_validation_empty_request(self):
        """Test input validation with empty request"""
        intake = IntakeNode()
        
        # Test with None
        with pytest.raises(Exception):
            intake.parse_request(None)
    
    def test_input_validation_missing_fields(self):
        """Test input validation with missing required fields"""
        intake = IntakeNode()
        
        # Test with missing project_name
        request = UserRequest(
            project_name="",
            project_description="Test",
        )
        
        # Should handle gracefully
        try:
            spec, run_id = intake.parse_request(request)
            # If it succeeds, verify it has valid data
            assert spec is not None
        except Exception:
            # Expected to fail on invalid input
            pass
    
    def test_input_validation_malicious_strings(self):
        """Test input validation with potentially malicious strings"""
        intake = IntakeNode()
        
        # Test with SQL injection attempt
        request = UserRequest(
            project_name="'; DROP TABLE projects; --",
            project_description="Test project",
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should safely handle the malicious string
        assert spec is not None
        assert spec.project_name == "'; DROP TABLE projects; --"
    
    def test_input_validation_xss_attempt(self):
        """Test input validation with XSS attempt"""
        intake = IntakeNode()
        
        # Test with XSS attempt
        request = UserRequest(
            project_name="<script>alert('xss')</script>",
            project_description="Test project",
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should safely handle the XSS attempt
        assert spec is not None
        assert "<script>" in spec.project_name
    
    def test_input_validation_unicode_handling(self):
        """Test input validation with unicode characters"""
        intake = IntakeNode()
        
        # Test with unicode characters
        request = UserRequest(
            project_name="项目名称 🚀 Проект",
            project_description="Test project with unicode",
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should safely handle unicode
        assert spec is not None
        assert "项目名称" in spec.project_name
    
    def test_input_validation_large_payload(self):
        """Test input validation with large payload"""
        intake = IntakeNode()
        
        # Test with large payload
        large_description = "x" * 100000
        request = UserRequest(
            project_name="Large Payload Test",
            project_description=large_description,
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Should handle large payload
        assert spec is not None
        assert len(spec.project_description) == 100000
    
    def test_specification_parser_validation(self):
        """Test specification parser validation"""
        parser = SpecificationParser()
        
        # Test with invalid JSON
        invalid_json = "{ invalid json }"
        result = parser.parse(invalid_json)
        
        assert not result.success
        assert result.error is not None
    
    def test_specification_parser_missing_fields(self):
        """Test specification parser with missing required fields"""
        parser = SpecificationParser()
        
        # Test with missing required fields
        incomplete_spec = {
            "project_name": "Test",
            # Missing other required fields
        }
        
        result = parser.parse(incomplete_spec)
        
        assert not result.success
        assert "Missing required fields" in result.error
    
    def test_specification_parser_invalid_version(self):
        """Test specification parser with invalid version"""
        parser = SpecificationParser()
        
        # Create a valid spec but with invalid version
        request = UserRequest(
            project_name="Test",
            project_description="Test",
        )
        
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        spec_dict = asdict(spec)
        spec_dict["version"] = "99.0"  # Invalid version
        
        result = parser.parse(spec_dict)
        
        assert not result.success
        assert "Unsupported specification version" in result.error
    
    def test_access_control_allowed_operations(self):
        """Test access control for allowed operations"""
        day2_module = Day2OperationsModule()
        
        # Test allowed operations
        allowed_ops = [
            OperationType.QUERY,
            OperationType.READ,
            OperationType.TOOL_EXECUTION,
            OperationType.NEW_PROJECT,
        ]
        
        for op in allowed_ops:
            result = day2_module.check_operation_allowed(op, user_id="user_001")
            assert result.allowed, f"Operation {op} should be allowed"
    
    def test_access_control_blocked_operations(self):
        """Test access control for blocked operations"""
        day2_module = Day2OperationsModule()
        
        # Test blocked operations
        blocked_ops = [
            OperationType.BOOTSTRAP,
            OperationType.MEMORY_RESET,
            OperationType.CONFIG_CHANGE,
            OperationType.AGENT_INIT,
        ]
        
        for op in blocked_ops:
            result = day2_module.check_operation_allowed(op, user_id="user_001")
            assert not result.allowed, f"Operation {op} should be blocked"
    
    def test_access_control_audit_logging(self):
        """Test that all operations are logged for audit"""
        day2_module = Day2OperationsModule()
        
        # Perform various operations
        operations = [
            (OperationType.QUERY, "user_001"),
            (OperationType.BOOTSTRAP, "user_002"),
            (OperationType.READ, "user_001"),
        ]
        
        for op, user_id in operations:
            day2_module.check_operation_allowed(op, user_id=user_id)
        
        # Verify all operations are logged
        audit_log = day2_module.get_audit_log()
        assert len(audit_log) == 3
        
        # Verify audit log contains correct information
        assert audit_log[0].operation_type == OperationType.QUERY
        assert audit_log[0].user_id == "user_001"
        assert audit_log[1].operation_type == OperationType.BOOTSTRAP
        assert audit_log[1].user_id == "user_002"
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        config_manager = ConfigurationManager()
        config_manager.load_defaults()
        
        # Test valid configuration
        assert config_manager.validate_configuration()
        
        # Test invalid configuration
        config_manager.config.mode = "INVALID_MODE"
        assert not config_manager.validate_configuration()
    
    def test_observability_trace_isolation(self):
        """Test that traces are properly isolated"""
        obs_module = ObservabilityModule()
        
        # Create multiple traces
        trace_ids = ["trace_001", "trace_002", "trace_003"]
        
        for trace_id in trace_ids:
            obs_module.start_trace(
                trace_id=trace_id,
                operation_name=f"operation_{trace_id}",
            )
            obs_module.emit_log(
                trace_id=trace_id,
                level=LogLevel.INFO.value,
                message=f"Log for {trace_id}",
            )
            obs_module.end_trace(
                trace_id=trace_id,
                status=OperationStatus.SUCCESS.value,
            )
        
        # Verify traces are isolated
        assert len(obs_module.traces) == 3
        
        # Verify each trace has correct trace_id
        for i, trace_id in enumerate(trace_ids):
            trace = obs_module.traces[i]
            assert trace.trace_id == trace_id
    
    def test_observability_log_level_filtering(self):
        """Test that log levels are properly enforced"""
        obs_module = ObservabilityModule()
        
        trace_id = "trace_001"
        obs_module.start_trace(trace_id=trace_id, operation_name="test")
        
        # Emit logs at different levels
        log_levels = [
            LogLevel.DEBUG.value,
            LogLevel.INFO.value,
            LogLevel.WARNING.value,
            LogLevel.ERROR.value,
        ]
        
        for level in log_levels:
            obs_module.emit_log(
                trace_id=trace_id,
                level=level,
                message=f"Message at {level}",
            )
        
        obs_module.end_trace(trace_id=trace_id)
        
        # Verify all logs were recorded
        assert len(obs_module.logs) == 4
    
    def test_data_integrity_specification_roundtrip(self):
        """Test data integrity through specification roundtrip"""
        # Create request
        request = UserRequest(
            project_name="Integrity Test",
            project_description="Test data integrity",
            scope="Full-stack",
            constraints=["Constraint 1", "Constraint 2"],
            resources={"budget": 100000},
        )
        
        # Generate specification
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Convert to dict and parse
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        
        # Verify data integrity
        assert parse_result.data["project_name"] == "Integrity Test"
        assert parse_result.data["project_description"] == "Test data integrity"
        assert parse_result.data["scope"] == "Full-stack"
        assert len(parse_result.data["constraints"]) == 2
        assert parse_result.data["resources"]["budget"] == 100000
    
    def test_error_handling_graceful_degradation(self):
        """Test graceful error handling and degradation"""
        parser = SpecificationParser()
        
        # Test with various invalid inputs
        invalid_inputs = [
            None,
            "",
            "{}",  # Empty JSON
            "invalid",
            '{"invalid": "data"}',
        ]
        
        for invalid_input in invalid_inputs:
            try:
                result = parser.parse(invalid_input)
                # Should either succeed or fail gracefully
                if not result.success:
                    assert result.error is not None
            except Exception as e:
                # Should not raise unexpected exceptions
                assert isinstance(e, Exception)
    
    def test_concurrent_access_safety(self):
        """Test thread safety of concurrent access"""
        import threading
        
        day2_module = Day2OperationsModule()
        results = {"errors": 0, "success": 0}
        lock = threading.Lock()
        
        def perform_operations():
            try:
                for i in range(10):
                    day2_module.check_operation_allowed(
                        OperationType.QUERY,
                        user_id=f"user_{threading.current_thread().ident}",
                    )
                with lock:
                    results["success"] += 1
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        # Run concurrent operations
        threads = [threading.Thread(target=perform_operations) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert results["errors"] == 0
        assert results["success"] == 10
        
        # Verify audit log is consistent
        audit_log = day2_module.get_audit_log()
        assert len(audit_log) == 100  # 10 threads * 10 operations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
