"""
End-to-End Integration Tests

Tests the complete Kabbalah system workflow.
"""

import pytest
import time
import json
from src.kabbalah.intake_node import IntakeNode
from src.kabbalah.models import UserRequest, Specification
from src.kabbalah.specification_parser import SpecificationParser
from src.kabbalah.specification_pretty_printer import SpecificationPrettyPrinter, OutputFormat
from src.kabbalah.configuration_manager import ConfigurationManager
from src.kabbalah.day2_operations import Day2OperationsModule, OperationType
from src.kabbalah.observability.observability_module import ObservabilityModule, LogLevel, OperationStatus


class TestE2EIntegration:
    """End-to-End Integration Tests"""
    
    def test_complete_workflow(self):
        """Test complete workflow from request to specification"""
        # Step 1: Create user request
        request = UserRequest(
            project_name="E-Commerce Platform",
            project_description="Build a scalable e-commerce platform with payment processing",
            scope="Full-stack web application",
            constraints=["Must support 10k concurrent users"],
            resources={"budget": 50000},
        )
        
        # Step 2: Parse request and generate specification
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        assert spec is not None
        assert run_id is not None
        assert spec.project_name == "E-Commerce Platform"
        
        # Step 3: Convert specification to dict and parse
        from dataclasses import asdict
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        
        assert parse_result.success
        assert parse_result.data is not None
        
        # Step 4: Format specification
        printer = SpecificationPrettyPrinter()
        json_output = printer.format_json(parse_result.data)
        text_output = printer.format_text(parse_result.data)
        
        assert isinstance(json_output, str)
        assert isinstance(text_output, str)
        assert "E-Commerce Platform" in text_output
    
    def test_configuration_workflow(self):
        """Test configuration loading and validation"""
        # Step 1: Create configuration manager
        config_manager = ConfigurationManager()
        
        # Step 2: Load defaults
        config_manager.load_defaults()
        
        # Step 3: Validate configuration
        assert config_manager.validate_configuration()
        
        # Step 4: Export configuration
        config_dict = config_manager.to_dict()
        config_json = config_manager.to_json()
        
        assert isinstance(config_dict, dict)
        assert isinstance(config_json, str)
        
        # Step 5: Parse exported configuration
        parser = SpecificationParser()
        # Configuration should be valid JSON
        parsed = json.loads(config_json)
        assert parsed["mode"] == "DAY1"
    
    def test_day2_operations_workflow(self):
        """Test Day 2 operations enforcement"""
        # Step 1: Create Day 2 operations module
        day2_module = Day2OperationsModule()
        
        # Step 2: Check allowed operations
        query_result = day2_module.check_operation_allowed(
            OperationType.QUERY,
            user_id="user_001",
        )
        assert query_result.allowed
        
        # Step 3: Check blocked operations
        bootstrap_result = day2_module.check_operation_allowed(
            OperationType.BOOTSTRAP,
            user_id="user_001",
        )
        assert not bootstrap_result.allowed
        
        # Step 4: Get audit log
        audit_log = day2_module.get_audit_log()
        assert len(audit_log) == 2
        
        # Step 5: Get statistics
        stats = day2_module.get_statistics()
        assert stats["total_entries"] == 2
        assert stats["allowed_operations"] == 1
        assert stats["blocked_operations"] == 1
    
    def test_observability_workflow(self):
        """Test observability module workflow"""
        # Step 1: Create observability module
        obs_module = ObservabilityModule()
        
        # Step 2: Start trace
        trace = obs_module.start_trace(
            trace_id="trace_001",
            operation_name="test_operation",
            metadata={"key": "value"},
        )
        assert trace is not None
        
        # Step 3: Emit logs
        obs_module.emit_log(
            trace_id="trace_001",
            level=LogLevel.INFO.value,
            message="Operation started",
        )
        
        # Step 4: Emit metrics
        obs_module.emit_metric(
            name="operation_duration",
            value=100.5,
            tags={"operation": "test"},
        )
        
        # Step 5: End trace
        time.sleep(0.01)
        completed_trace = obs_module.end_trace(
            trace_id="trace_001",
            status=OperationStatus.SUCCESS.value,
        )
        assert completed_trace is not None
        assert completed_trace.duration_ms > 0
        
        # Step 6: Get statistics
        stats = obs_module.get_statistics()
        assert stats["traces"]["total"] == 1
        assert stats["logs"]["total"] == 1
        assert stats["metrics"]["total"] == 1
        
        # Step 7: Export data
        json_export = obs_module.export_json()
        exported_data = json.loads(json_export)
        assert len(exported_data["traces"]) == 1
        assert len(exported_data["logs"]) == 1
        assert len(exported_data["metrics"]) == 1
    
    def test_multi_phase_workflow(self):
        """Test workflow spanning multiple phases"""
        # Phase 1: Create request
        request = UserRequest(
            project_name="Test Project",
            project_description="A test project",
        )
        
        # Phase 2: Generate specification
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Phase 3: Parse and validate specification
        from dataclasses import asdict
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        assert parse_result.success
        
        # Phase 4: Format specification
        printer = SpecificationPrettyPrinter()
        formatted = printer.format_json(parse_result.data)
        assert isinstance(formatted, str)
        
        # Phase 5: Load configuration
        config_manager = ConfigurationManager()
        config_manager.load_defaults()
        assert config_manager.validate_configuration()
        
        # Phase 6: Check Day 2 operations
        day2_module = Day2OperationsModule()
        result = day2_module.check_operation_allowed(
            OperationType.NEW_PROJECT,
            user_id="user_001",
        )
        assert result.allowed
        
        # Phase 7: Track with observability
        obs_module = ObservabilityModule()
        obs_module.start_trace(
            trace_id=run_id,
            operation_name="project_creation",
        )
        obs_module.emit_log(
            trace_id=run_id,
            level=LogLevel.INFO.value,
            message="Project created successfully",
        )
        obs_module.end_trace(
            trace_id=run_id,
            status=OperationStatus.SUCCESS.value,
        )
        
        # Verify all phases worked together
        assert spec is not None
        assert parse_result.success
        assert config_manager.config.mode == "DAY1"
        assert result.allowed
        assert len(obs_module.traces) == 1
    
    def test_error_handling_workflow(self):
        """Test error handling across phases"""
        # Test invalid request
        intake = IntakeNode()
        with pytest.raises(Exception):
            intake.parse_request(None)
        
        # Test invalid specification
        parser = SpecificationParser()
        invalid_spec = {"invalid": "data"}
        result = parser.parse(invalid_spec)
        assert not result.success
        
        # Test invalid configuration
        config_manager = ConfigurationManager()
        config_manager.config.mode = "INVALID"
        assert not config_manager.validate_configuration()
    
    def test_concurrent_operations(self):
        """Test concurrent operations across modules"""
        import threading
        
        results = {"success": 0, "error": 0}
        
        def perform_operations():
            try:
                # Create modules
                obs_module = ObservabilityModule()
                day2_module = Day2OperationsModule()
                
                # Perform operations
                trace = obs_module.start_trace(
                    trace_id=f"trace_{threading.current_thread().ident}",
                    operation_name="concurrent_op",
                )
                
                result = day2_module.check_operation_allowed(
                    OperationType.QUERY,
                    user_id=f"user_{threading.current_thread().ident}",
                )
                
                obs_module.end_trace(
                    trace_id=f"trace_{threading.current_thread().ident}",
                    status=OperationStatus.SUCCESS.value,
                )
                
                results["success"] += 1
            except Exception as e:
                results["error"] += 1
        
        # Run concurrent operations
        threads = [threading.Thread(target=perform_operations) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert results["success"] == 10
        assert results["error"] == 0
    
    def test_data_consistency(self):
        """Test data consistency across phases"""
        # Create specification
        request = UserRequest(
            project_name="Consistency Test",
            project_description="Test data consistency",
        )
        
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Parse specification
        from dataclasses import asdict
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        
        # Format specification
        printer = SpecificationPrettyPrinter()
        json_output = printer.format_json(parse_result.data)
        
        # Re-parse formatted output
        reparsed = json.loads(json_output)
        
        # Verify consistency
        assert reparsed["project_name"] == "Consistency Test"
        assert reparsed["run_id"] == run_id
        assert reparsed["project_description"] == "Test data consistency"
    
    def test_performance_metrics(self):
        """Test performance of integrated workflow"""
        start_time = time.time()
        
        # Create request
        request = UserRequest(
            project_name="Performance Test",
            project_description="Test performance",
        )
        
        # Generate specification
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Parse specification
        parser = SpecificationParser()
        parse_result = parser.parse(spec)
        
        # Format specification
        printer = SpecificationPrettyPrinter()
        printer.format_json(parse_result.data)
        
        # Load configuration
        config_manager = ConfigurationManager()
        config_manager.load_defaults()
        
        # Check Day 2 operations
        day2_module = Day2OperationsModule()
        day2_module.check_operation_allowed(OperationType.QUERY)
        
        # Track with observability
        obs_module = ObservabilityModule()
        obs_module.start_trace(trace_id=run_id, operation_name="perf_test")
        obs_module.end_trace(trace_id=run_id)
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed_time < 1.0
    
    def test_audit_trail(self):
        """Test complete audit trail of operations"""
        # Create Day 2 module
        day2_module = Day2OperationsModule()
        
        # Perform various operations
        operations = [
            (OperationType.QUERY, "user_001"),
            (OperationType.READ, "user_002"),
            (OperationType.TOOL_EXECUTION, "user_001"),
            (OperationType.BOOTSTRAP, "user_003"),
            (OperationType.NEW_PROJECT, "user_002"),
        ]
        
        for op_type, user_id in operations:
            day2_module.check_operation_allowed(op_type, user_id=user_id)
        
        # Get audit log
        audit_log = day2_module.get_audit_log()
        assert len(audit_log) == 5
        
        # Verify audit trail
        assert audit_log[0].operation_type == OperationType.QUERY
        assert audit_log[0].user_id == "user_001"
        
        assert audit_log[3].operation_type == OperationType.BOOTSTRAP
        assert audit_log[3].user_id == "user_003"
        
        # Export audit trail
        exported = day2_module.export_audit_log()
        assert len(exported) == 5
        assert all(isinstance(e, dict) for e in exported)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
