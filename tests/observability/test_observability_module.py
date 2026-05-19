"""
Tests for Observability Module

Tests the ObservabilityModule implementation.
"""

import pytest
import time
import json
from src.kabbalah.observability.observability_module import (
    ObservabilityModule,
    Trace,
    LogEntry,
    Metric,
    LogLevel,
    OperationStatus,
)


class TestObservabilityModule:
    """Test Observability Module"""
    
    def test_module_initialization(self):
        """Test module initialization"""
        module = ObservabilityModule()
        
        assert module is not None
        assert len(module.traces) == 0
        assert len(module.logs) == 0
        assert len(module.metrics) == 0
    
    def test_start_and_end_trace(self):
        """Test starting and ending a trace"""
        module = ObservabilityModule()
        
        # Start trace
        trace = module.start_trace(
            trace_id="test_trace_001",
            operation_name="test_operation",
            metadata={"key": "value"},
        )
        
        assert trace.trace_id == "test_trace_001"
        assert trace.operation_name == "test_operation"
        assert trace.metadata["key"] == "value"
        assert trace.end_time is None
        
        # End trace
        time.sleep(0.01)  # Small delay to ensure duration > 0
        completed_trace = module.end_trace(
            trace_id="test_trace_001",
            status=OperationStatus.SUCCESS.value,
        )
        
        assert completed_trace is not None
        assert completed_trace.end_time is not None
        assert completed_trace.duration_ms > 0
        assert completed_trace.status == OperationStatus.SUCCESS.value
        assert len(module.traces) == 1
    
    def test_emit_log(self):
        """Test emitting logs"""
        module = ObservabilityModule()
        
        log_entry = module.emit_log(
            trace_id="test_trace_001",
            level=LogLevel.INFO.value,
            message="Test log message",
            context={"key": "value"},
        )
        
        assert log_entry.trace_id == "test_trace_001"
        assert log_entry.level == LogLevel.INFO.value
        assert log_entry.message == "Test log message"
        assert log_entry.context["key"] == "value"
        assert len(module.logs) == 1
    
    def test_emit_metric(self):
        """Test emitting metrics"""
        module = ObservabilityModule()
        
        metric = module.emit_metric(
            name="test_metric",
            value=42.5,
            tags={"service": "test"},
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.tags["service"] == "test"
        assert len(module.metrics) == 1
    
    def test_get_traces_with_filter(self):
        """Test getting traces with filters"""
        module = ObservabilityModule()
        
        # Create multiple traces
        module.start_trace("trace_001", "operation_a")
        module.end_trace("trace_001", OperationStatus.SUCCESS.value)
        
        module.start_trace("trace_002", "operation_b")
        module.end_trace("trace_002", OperationStatus.ERROR.value)
        
        # Get all traces
        all_traces = module.get_traces()
        assert len(all_traces) == 2
        
        # Filter by trace_id
        traces = module.get_traces(trace_id="trace_001")
        assert len(traces) == 1
        assert traces[0].trace_id == "trace_001"
        
        # Filter by operation_name
        traces = module.get_traces(operation_name="operation_a")
        assert len(traces) == 1
        assert traces[0].operation_name == "operation_a"
        
        # Filter by status
        traces = module.get_traces(status=OperationStatus.ERROR.value)
        assert len(traces) == 1
        assert traces[0].status == OperationStatus.ERROR.value
    
    def test_get_logs_with_filter(self):
        """Test getting logs with filters"""
        module = ObservabilityModule()
        
        # Create multiple logs
        module.emit_log("trace_001", LogLevel.INFO.value, "Info message")
        module.emit_log("trace_001", LogLevel.ERROR.value, "Error message")
        module.emit_log("trace_002", LogLevel.WARNING.value, "Warning message")
        
        # Get all logs
        all_logs = module.get_logs()
        assert len(all_logs) == 3
        
        # Filter by trace_id
        logs = module.get_logs(trace_id="trace_001")
        assert len(logs) == 2
        
        # Filter by level
        logs = module.get_logs(level=LogLevel.ERROR.value)
        assert len(logs) == 1
        assert logs[0].message == "Error message"
    
    def test_get_metrics_with_filter(self):
        """Test getting metrics with filters"""
        module = ObservabilityModule()
        
        # Create multiple metrics
        module.emit_metric("cpu_usage", 45.2)
        module.emit_metric("memory_usage", 78.5)
        module.emit_metric("cpu_usage", 48.1)
        
        # Get all metrics
        all_metrics = module.get_metrics()
        assert len(all_metrics) == 3
        
        # Filter by name
        metrics = module.get_metrics(name="cpu_usage")
        assert len(metrics) == 2
        assert all(m.name == "cpu_usage" for m in metrics)
    
    def test_get_statistics(self):
        """Test getting statistics"""
        module = ObservabilityModule()
        
        # Create traces
        module.start_trace("trace_001", "operation_a")
        module.end_trace("trace_001", OperationStatus.SUCCESS.value)
        
        module.start_trace("trace_002", "operation_b")
        module.end_trace("trace_002", OperationStatus.ERROR.value)
        
        # Create logs
        module.emit_log("trace_001", LogLevel.INFO.value, "Info")
        module.emit_log("trace_002", LogLevel.ERROR.value, "Error")
        
        # Create metrics
        module.emit_metric("metric_1", 10.0)
        module.emit_metric("metric_2", 20.0)
        
        stats = module.get_statistics()
        
        assert stats["traces"]["total"] == 2
        assert stats["traces"]["success"] == 1
        assert stats["traces"]["error"] == 1
        assert stats["logs"]["total"] == 2
        assert stats["logs"]["info"] == 1
        assert stats["logs"]["error"] == 1
        assert stats["metrics"]["total"] == 2
        assert stats["metrics"]["unique_names"] == 2
    
    def test_clear(self):
        """Test clearing observability data"""
        module = ObservabilityModule()
        
        # Add data
        module.start_trace("trace_001", "operation")
        module.end_trace("trace_001")
        module.emit_log("trace_001", LogLevel.INFO.value, "Message")
        module.emit_metric("metric", 10.0)
        
        assert len(module.traces) == 1
        assert len(module.logs) == 1
        assert len(module.metrics) == 1
        
        # Clear
        module.clear()
        
        assert len(module.traces) == 0
        assert len(module.logs) == 0
        assert len(module.metrics) == 0
    
    def test_export_json(self):
        """Test exporting data as JSON"""
        module = ObservabilityModule()
        
        # Add data
        module.start_trace("trace_001", "operation")
        module.end_trace("trace_001")
        module.emit_log("trace_001", LogLevel.INFO.value, "Message")
        module.emit_metric("metric", 10.0)
        
        # Export
        json_str = module.export_json()
        data = json.loads(json_str)
        
        assert "traces" in data
        assert "logs" in data
        assert "metrics" in data
        assert "statistics" in data
        assert len(data["traces"]) == 1
        assert len(data["logs"]) == 1
        assert len(data["metrics"]) == 1
    
    def test_max_capacity_eviction(self):
        """Test that old data is evicted when max capacity is reached"""
        module = ObservabilityModule(max_traces=3, max_logs=3, max_metrics=3)
        
        # Add traces beyond capacity
        for i in range(5):
            module.start_trace(f"trace_{i:03d}", "operation")
            module.end_trace(f"trace_{i:03d}")
        
        # Should only have 3 traces (oldest evicted)
        assert len(module.traces) == 3
        assert module.traces[0].trace_id == "trace_002"
        
        # Add logs beyond capacity
        for i in range(5):
            module.emit_log(f"trace_{i:03d}", LogLevel.INFO.value, f"Message {i}")
        
        # Should only have 3 logs
        assert len(module.logs) == 3
        
        # Add metrics beyond capacity
        for i in range(5):
            module.emit_metric(f"metric_{i}", float(i))
        
        # Should only have 3 metrics
        assert len(module.metrics) == 3


class TestTrace:
    """Test Trace class"""
    
    def test_trace_creation(self):
        """Test creating a trace"""
        trace = Trace(
            trace_id="test_001",
            operation_name="test_op",
            start_time=time.time(),
        )
        
        assert trace.trace_id == "test_001"
        assert trace.operation_name == "test_op"
        assert trace.status == OperationStatus.SUCCESS.value
    
    def test_trace_to_dict(self):
        """Test converting trace to dictionary"""
        trace = Trace(
            trace_id="test_001",
            operation_name="test_op",
            start_time=time.time(),
            metadata={"key": "value"},
        )
        
        trace_dict = trace.to_dict()
        assert trace_dict["trace_id"] == "test_001"
        assert trace_dict["operation_name"] == "test_op"
        assert trace_dict["metadata"]["key"] == "value"


class TestLogEntry:
    """Test LogEntry class"""
    
    def test_log_entry_creation(self):
        """Test creating a log entry"""
        log = LogEntry(
            trace_id="test_001",
            level=LogLevel.INFO.value,
            message="Test message",
            timestamp=time.time(),
        )
        
        assert log.trace_id == "test_001"
        assert log.level == LogLevel.INFO.value
        assert log.message == "Test message"
    
    def test_log_entry_to_dict(self):
        """Test converting log entry to dictionary"""
        log = LogEntry(
            trace_id="test_001",
            level=LogLevel.INFO.value,
            message="Test message",
            timestamp=time.time(),
            context={"key": "value"},
        )
        
        log_dict = log.to_dict()
        assert log_dict["trace_id"] == "test_001"
        assert log_dict["level"] == LogLevel.INFO.value
        assert log_dict["context"]["key"] == "value"


class TestMetric:
    """Test Metric class"""
    
    def test_metric_creation(self):
        """Test creating a metric"""
        metric = Metric(
            name="test_metric",
            value=42.5,
            timestamp=time.time(),
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary"""
        metric = Metric(
            name="test_metric",
            value=42.5,
            timestamp=time.time(),
            tags={"service": "test"},
        )
        
        metric_dict = metric.to_dict()
        assert metric_dict["name"] == "test_metric"
        assert metric_dict["value"] == 42.5
        assert metric_dict["tags"]["service"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
