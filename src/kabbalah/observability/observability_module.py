"""
Observability Module

Collects traces, logs, and metrics for complete system visibility.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import json

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationStatus(Enum):
    """Operation status"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


@dataclass
class Trace:
    """Trace information"""
    trace_id: str
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = OperationStatus.SUCCESS.value
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class LogEntry:
    """Log entry"""
    trace_id: str
    level: str
    message: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class Metric:
    """Metric data"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


class ObservabilityModule:
    """
    Collects traces, logs, and metrics for system observability.
    
    Features:
    - Trace collection with hierarchical trace_id
    - Structured logging
    - Metric collection
    - Thread-safe operations
    - In-memory storage with optional export
    """
    
    def __init__(
        self,
        max_traces: int = 10000,
        max_logs: int = 50000,
        max_metrics: int = 100000,
    ):
        """
        Initialize observability module.
        
        Args:
            max_traces: Maximum traces to store
            max_logs: Maximum logs to store
            max_metrics: Maximum metrics to store
        """
        self.max_traces = max_traces
        self.max_logs = max_logs
        self.max_metrics = max_metrics
        
        self.traces: List[Trace] = []
        self.logs: List[LogEntry] = []
        self.metrics: List[Metric] = []
        
        self._lock = threading.Lock()
        self._active_traces: Dict[str, Trace] = {}
    
    def start_trace(
        self,
        trace_id: str,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Trace:
        """
        Start a trace.
        
        Args:
            trace_id: Unique trace identifier
            operation_name: Name of operation
            metadata: Additional metadata
            
        Returns:
            Trace object
        """
        trace = Trace(
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {},
        )
        
        with self._lock:
            self._active_traces[trace_id] = trace
        
        logger.debug(f"Trace started: {trace_id} - {operation_name}")
        return trace
    
    def end_trace(
        self,
        trace_id: str,
        status: str = OperationStatus.SUCCESS.value,
        error: Optional[str] = None,
    ) -> Optional[Trace]:
        """
        End a trace.
        
        Args:
            trace_id: Trace identifier
            status: Operation status
            error: Error message if failed
            
        Returns:
            Completed trace or None
        """
        with self._lock:
            if trace_id not in self._active_traces:
                logger.warning(f"Trace not found: {trace_id}")
                return None
            
            trace = self._active_traces.pop(trace_id)
            trace.end_time = time.time()
            trace.status = status
            trace.error = error
            trace.duration_ms = (trace.end_time - trace.start_time) * 1000
            
            # Add to traces list (with eviction if needed)
            if len(self.traces) >= self.max_traces:
                self.traces.pop(0)
            self.traces.append(trace)
        
        logger.debug(f"Trace ended: {trace_id} - {status} ({trace.duration_ms:.2f}ms)")
        return trace
    
    def emit_log(
        self,
        trace_id: str,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """
        Emit a log entry.
        
        Args:
            trace_id: Trace identifier
            level: Log level
            message: Log message
            context: Additional context
            
        Returns:
            Log entry
        """
        log_entry = LogEntry(
            trace_id=trace_id,
            level=level,
            message=message,
            timestamp=time.time(),
            context=context or {},
        )
        
        with self._lock:
            # Add to logs list (with eviction if needed)
            if len(self.logs) >= self.max_logs:
                self.logs.pop(0)
            self.logs.append(log_entry)
        
        # Also log using Python logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{trace_id}] {message}")
        
        return log_entry
    
    def emit_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """
        Emit a metric.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Metric tags
            
        Returns:
            Metric object
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
        )
        
        with self._lock:
            # Add to metrics list (with eviction if needed)
            if len(self.metrics) >= self.max_metrics:
                self.metrics.pop(0)
            self.metrics.append(metric)
        
        logger.debug(f"Metric emitted: {name}={value}")
        return metric
    
    def get_traces(
        self,
        trace_id: Optional[str] = None,
        operation_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Trace]:
        """
        Get traces with optional filtering.
        
        Args:
            trace_id: Filter by trace_id
            operation_name: Filter by operation_name
            status: Filter by status
            
        Returns:
            List of traces
        """
        with self._lock:
            traces = self.traces.copy()
        
        # Apply filters
        if trace_id:
            traces = [t for t in traces if t.trace_id == trace_id]
        if operation_name:
            traces = [t for t in traces if t.operation_name == operation_name]
        if status:
            traces = [t for t in traces if t.status == status]
        
        return traces
    
    def get_logs(
        self,
        trace_id: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[LogEntry]:
        """
        Get logs with optional filtering.
        
        Args:
            trace_id: Filter by trace_id
            level: Filter by level
            
        Returns:
            List of logs
        """
        with self._lock:
            logs = self.logs.copy()
        
        # Apply filters
        if trace_id:
            logs = [l for l in logs if l.trace_id == trace_id]
        if level:
            logs = [l for l in logs if l.level == level]
        
        return logs
    
    def get_metrics(
        self,
        name: Optional[str] = None,
    ) -> List[Metric]:
        """
        Get metrics with optional filtering.
        
        Args:
            name: Filter by metric name
            
        Returns:
            List of metrics
        """
        with self._lock:
            metrics = self.metrics.copy()
        
        # Apply filters
        if name:
            metrics = [m for m in metrics if m.name == name]
        
        return metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get observability statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            traces = self.traces.copy()
            logs = self.logs.copy()
            metrics = self.metrics.copy()
        
        # Calculate trace statistics
        trace_stats = {
            "total": len(traces),
            "success": len([t for t in traces if t.status == OperationStatus.SUCCESS.value]),
            "error": len([t for t in traces if t.status == OperationStatus.ERROR.value]),
            "avg_duration_ms": sum(t.duration_ms for t in traces) / len(traces) if traces else 0,
        }
        
        # Calculate log statistics
        log_stats = {
            "total": len(logs),
            "debug": len([l for l in logs if l.level == LogLevel.DEBUG.value]),
            "info": len([l for l in logs if l.level == LogLevel.INFO.value]),
            "warning": len([l for l in logs if l.level == LogLevel.WARNING.value]),
            "error": len([l for l in logs if l.level == LogLevel.ERROR.value]),
        }
        
        # Calculate metric statistics
        metric_stats = {
            "total": len(metrics),
            "unique_names": len(set(m.name for m in metrics)),
        }
        
        return {
            "traces": trace_stats,
            "logs": log_stats,
            "metrics": metric_stats,
            "storage": {
                "traces_capacity": f"{len(traces)}/{self.max_traces}",
                "logs_capacity": f"{len(logs)}/{self.max_logs}",
                "metrics_capacity": f"{len(metrics)}/{self.max_metrics}",
            },
        }
    
    def clear(self) -> None:
        """Clear all observability data"""
        with self._lock:
            self.traces.clear()
            self.logs.clear()
            self.metrics.clear()
            self._active_traces.clear()
        
        logger.info("Observability data cleared")
    
    def export_json(self) -> str:
        """
        Export all observability data as JSON.
        
        Returns:
            JSON string
        """
        with self._lock:
            traces = self.traces.copy()
            logs = self.logs.copy()
            metrics = self.metrics.copy()
        
        # Calculate statistics without holding the lock
        trace_stats = {
            "total": len(traces),
            "success": len([t for t in traces if t.status == OperationStatus.SUCCESS.value]),
            "error": len([t for t in traces if t.status == OperationStatus.ERROR.value]),
            "avg_duration_ms": sum(t.duration_ms for t in traces) / len(traces) if traces else 0,
        }
        
        log_stats = {
            "total": len(logs),
            "debug": len([l for l in logs if l.level == LogLevel.DEBUG.value]),
            "info": len([l for l in logs if l.level == LogLevel.INFO.value]),
            "warning": len([l for l in logs if l.level == LogLevel.WARNING.value]),
            "error": len([l for l in logs if l.level == LogLevel.ERROR.value]),
        }
        
        metric_stats = {
            "total": len(metrics),
            "unique_names": len(set(m.name for m in metrics)),
        }
        
        statistics = {
            "traces": trace_stats,
            "logs": log_stats,
            "metrics": metric_stats,
            "storage": {
                "traces_capacity": f"{len(traces)}/{self.max_traces}",
                "logs_capacity": f"{len(logs)}/{self.max_logs}",
                "metrics_capacity": f"{len(metrics)}/{self.max_metrics}",
            },
        }
        
        data = {
            "traces": [t.to_dict() for t in traces],
            "logs": [l.to_dict() for l in logs],
            "metrics": [m.to_dict() for m in metrics],
            "statistics": statistics,
        }
        
        return json.dumps(data, indent=2, default=str)
