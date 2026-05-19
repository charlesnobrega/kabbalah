"""
Performance Benchmarking Tests for Phase 10

Tests performance characteristics of orchestration, decomposition, synthesis, and trace propagation.
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
from dataclasses import asdict


class TestPerformanceBenchmarks:
    """Performance Benchmarking Tests"""
    
    def test_orchestration_decomposition_performance(self):
        """Test performance of orchestration decomposition"""
        # Create a complex request
        request = UserRequest(
            project_name="Complex E-Commerce Platform",
            project_description="Build a scalable e-commerce platform with payment processing, inventory management, and analytics",
            scope="Full-stack web application with microservices",
            constraints=[
                "Must support 100k concurrent users",
                "99.99% uptime SLA",
                "Sub-100ms response time",
                "GDPR compliant",
                "PCI-DSS compliant",
            ],
            resources={
                "budget": 500000,
                "team_size": 20,
                "timeline_months": 12,
            },
            metadata={
                "industry": "e-commerce",
                "region": "global",
                "compliance": ["GDPR", "PCI-DSS"],
            },
        )
        
        # Measure orchestration decomposition time
        start_time = time.time()
        
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        decomposition_time = time.time() - start_time
        
        # Verify decomposition completed
        assert spec is not None
        assert run_id is not None
        assert len(spec.domains) > 0
        assert len(spec.dependencies) > 0
        
        # Performance assertion: decomposition should complete in < 500ms
        assert decomposition_time < 0.5, f"Decomposition took {decomposition_time:.3f}s, expected < 0.5s"
    
    def test_synthesis_performance(self):
        """Test performance of specification synthesis"""
        # Create request
        request = UserRequest(
            project_name="Synthesis Test Project",
            project_description="Test synthesis performance",
            scope="Full-stack application",
            constraints=["High performance required"],
            resources={"budget": 100000},
        )
        
        # Generate specification
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Measure synthesis time (parsing + formatting)
        start_time = time.time()
        
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        
        printer = SpecificationPrettyPrinter()
        json_output = printer.format_json(parse_result.data)
        text_output = printer.format_text(parse_result.data)
        
        # Try YAML if available
        try:
            yaml_output = printer.format_yaml(parse_result.data)
            assert isinstance(yaml_output, str)
        except Exception:
            # YAML not available, skip
            pass
        
        synthesis_time = time.time() - start_time
        
        # Verify synthesis completed
        assert parse_result.success
        assert isinstance(json_output, str)
        assert isinstance(text_output, str)
        
        # Performance assertion: synthesis should complete in < 200ms
        assert synthesis_time < 0.2, f"Synthesis took {synthesis_time:.3f}s, expected < 0.2s"
    
    def test_trace_propagation_performance(self):
        """Test performance of trace propagation through system"""
        obs_module = ObservabilityModule()
        
        # Measure trace propagation time
        start_time = time.time()
        
        # Create multiple traces
        num_traces = 100
        for i in range(num_traces):
            trace_id = f"trace_{i:03d}"
            obs_module.start_trace(
                trace_id=trace_id,
                operation_name=f"operation_{i}",
                metadata={"index": i},
            )
            
            # Emit logs
            for j in range(5):
                obs_module.emit_log(
                    trace_id=trace_id,
                    level=LogLevel.INFO.value,
                    message=f"Log message {j}",
                )
            
            # Emit metrics
            for j in range(3):
                obs_module.emit_metric(
                    name=f"metric_{j}",
                    value=float(j * 10),
                    tags={"trace": trace_id},
                )
            
            # End trace
            obs_module.end_trace(
                trace_id=trace_id,
                status=OperationStatus.SUCCESS.value,
            )
        
        propagation_time = time.time() - start_time
        
        # Verify traces were created
        assert len(obs_module.traces) == num_traces
        assert len(obs_module.logs) == num_traces * 5
        assert len(obs_module.metrics) == num_traces * 3
        
        # Performance assertion: 100 traces should complete in < 1 second
        assert propagation_time < 1.0, f"Trace propagation took {propagation_time:.3f}s, expected < 1.0s"
        
        # Per-trace performance: average < 10ms per trace
        avg_per_trace = propagation_time / num_traces
        assert avg_per_trace < 0.01, f"Average per-trace time {avg_per_trace:.3f}s, expected < 0.01s"
    
    def test_configuration_loading_performance(self):
        """Test performance of configuration loading"""
        config_manager = ConfigurationManager()
        
        # Measure configuration loading time
        start_time = time.time()
        
        config_manager.load_defaults()
        config_manager.validate_configuration()
        config_dict = config_manager.to_dict()
        config_json = config_manager.to_json()
        
        loading_time = time.time() - start_time
        
        # Verify configuration loaded
        assert config_manager.config is not None
        assert isinstance(config_dict, dict)
        assert isinstance(config_json, str)
        
        # Performance assertion: configuration loading should complete in < 100ms
        assert loading_time < 0.1, f"Configuration loading took {loading_time:.3f}s, expected < 0.1s"
    
    def test_day2_operations_performance(self):
        """Test performance of Day 2 operations checking"""
        day2_module = Day2OperationsModule()
        
        # Measure Day 2 operations performance
        start_time = time.time()
        
        # Check multiple operations
        num_operations = 1000
        for i in range(num_operations):
            op_type = OperationType.QUERY if i % 2 == 0 else OperationType.READ
            day2_module.check_operation_allowed(
                op_type,
                user_id=f"user_{i % 100}",
            )
        
        operations_time = time.time() - start_time
        
        # Verify operations were checked
        audit_log = day2_module.get_audit_log()
        assert len(audit_log) == num_operations
        
        # Performance assertion: 1000 operations should complete in < 500ms
        assert operations_time < 0.5, f"Operations checking took {operations_time:.3f}s, expected < 0.5s"
        
        # Per-operation performance: average < 0.5ms per operation
        avg_per_op = operations_time / num_operations
        assert avg_per_op < 0.0005, f"Average per-operation time {avg_per_op:.6f}s, expected < 0.0005s"
    
    def test_end_to_end_workflow_performance(self):
        """Test performance of complete end-to-end workflow"""
        # Create request
        request = UserRequest(
            project_name="E2E Performance Test",
            project_description="Test end-to-end workflow performance",
            scope="Full-stack application",
            constraints=["Performance critical"],
            resources={"budget": 100000},
        )
        
        # Measure complete workflow time
        start_time = time.time()
        
        # Phase 1: Orchestration
        intake = IntakeNode()
        spec, run_id = intake.parse_request(request)
        
        # Phase 2: Synthesis
        spec_dict = asdict(spec)
        parser = SpecificationParser()
        parse_result = parser.parse(spec_dict)
        
        printer = SpecificationPrettyPrinter()
        json_output = printer.format_json(parse_result.data)
        
        # Phase 3: Configuration
        config_manager = ConfigurationManager()
        config_manager.load_defaults()
        config_manager.validate_configuration()
        
        # Phase 4: Day 2 Operations
        day2_module = Day2OperationsModule()
        day2_module.check_operation_allowed(OperationType.NEW_PROJECT)
        
        # Phase 5: Observability
        obs_module = ObservabilityModule()
        obs_module.start_trace(trace_id=run_id, operation_name="e2e_workflow")
        obs_module.emit_log(trace_id=run_id, level=LogLevel.INFO.value, message="Workflow started")
        obs_module.end_trace(trace_id=run_id, status=OperationStatus.SUCCESS.value)
        
        workflow_time = time.time() - start_time
        
        # Verify workflow completed
        assert spec is not None
        assert parse_result.success
        assert config_manager.config is not None
        assert len(obs_module.traces) == 1
        
        # Performance assertion: complete workflow should complete in < 1 second
        assert workflow_time < 1.0, f"E2E workflow took {workflow_time:.3f}s, expected < 1.0s"
    
    def test_memory_efficiency(self):
        """Test memory efficiency of system"""
        import sys
        
        # Create multiple specifications
        requests = []
        for i in range(10):
            request = UserRequest(
                project_name=f"Project {i}",
                project_description=f"Description for project {i}",
                scope="Full-stack application",
                constraints=[f"Constraint {j}" for j in range(5)],
                resources={"budget": 100000 * (i + 1)},
            )
            requests.append(request)
        
        # Generate specifications
        intake = IntakeNode()
        specs = []
        for request in requests:
            spec, run_id = intake.parse_request(request)
            specs.append(spec)
        
        # Verify all specifications were created
        assert len(specs) == 10
        
        # Check that specifications are reasonable size
        for spec in specs:
            spec_dict = asdict(spec)
            spec_json = json.dumps(spec_dict)
            spec_size = sys.getsizeof(spec_json)
            
            # Each specification should be < 10KB
            assert spec_size < 10000, f"Specification size {spec_size} bytes, expected < 10000"
    
    def test_concurrent_workflow_performance(self):
        """Test performance of concurrent workflows"""
        import threading
        
        results = {
            "completed": 0,
            "failed": 0,
            "total_time": 0,
        }
        lock = threading.Lock()
        
        def run_workflow():
            try:
                start_time = time.time()
                
                # Create request
                request = UserRequest(
                    project_name="Concurrent Test",
                    project_description="Test concurrent workflow",
                )
                
                # Run workflow
                intake = IntakeNode()
                spec, run_id = intake.parse_request(request)
                
                spec_dict = asdict(spec)
                parser = SpecificationParser()
                parse_result = parser.parse(spec_dict)
                
                printer = SpecificationPrettyPrinter()
                printer.format_json(parse_result.data)
                
                elapsed = time.time() - start_time
                
                with lock:
                    results["completed"] += 1
                    results["total_time"] += elapsed
            except Exception as e:
                with lock:
                    results["failed"] += 1
        
        # Run concurrent workflows
        num_threads = 10
        threads = [threading.Thread(target=run_workflow) for _ in range(num_threads)]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        total_time = time.time() - start_time
        
        # Verify all workflows completed
        assert results["completed"] == num_threads
        assert results["failed"] == 0
        
        # Performance assertion: 10 concurrent workflows should complete in < 5 seconds
        assert total_time < 5.0, f"Concurrent workflows took {total_time:.3f}s, expected < 5.0s"
        
        # Average per-workflow time
        avg_time = results["total_time"] / num_threads
        assert avg_time < 1.0, f"Average workflow time {avg_time:.3f}s, expected < 1.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
