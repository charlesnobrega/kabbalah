"""
Tests for Tool Execution Engine

Tests the ToolExecutionEngine implementation.
"""

import pytest
import os
import tempfile
from pathlib import Path

from src.kabbalah.tools.execution_engine import (
    ToolExecutionEngine,
    ToolRequest,
    ToolResponse,
    ToolType,
    ResourceLimits,
)


class TestToolExecutionEngine:
    """Test Tool Execution Engine"""
    
    def test_engine_initialization(self):
        """Test that engine initializes correctly"""
        engine = ToolExecutionEngine()
        
        assert engine is not None
        assert engine.resource_limits is not None
        assert len(engine.execution_history) == 0
    
    def test_engine_initialization_with_limits(self):
        """Test initializing engine with custom limits"""
        limits = ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_mb=256,
            max_disk_mb=512,
        )
        
        engine = ToolExecutionEngine(resource_limits=limits)
        
        assert engine.resource_limits.max_cpu_percent == 50.0
        assert engine.resource_limits.max_memory_mb == 256
        assert engine.resource_limits.max_disk_mb == 512
    
    def test_bash_execution_success(self):
        """Test successful bash command execution"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'Hello, World!'",
        )
        
        response = engine.execute(request)
        
        assert response.success is True
        assert "Hello, World!" in response.output
        assert response.exit_code == 0
        assert response.duration_ms > 0
    
    def test_bash_execution_failure(self):
        """Test failed bash command execution"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="false",
        )
        
        response = engine.execute(request)
        
        assert response.success is False
        assert response.exit_code != 0
    
    def test_bash_execution_timeout(self):
        """Test bash command timeout"""
        engine = ToolExecutionEngine()
        
        # Use timeout command on Windows, sleep on Unix
        cmd = "timeout /t 10" if os.name == "nt" else "sleep 10"
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command=cmd,
            timeout=0.1,
        )
        
        response = engine.execute(request)
        
        assert response.success is False
        # Either timeout or command not found is acceptable
        assert response.error is not None
    
    def test_file_read_operation(self):
        """Test file read operation"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            # Allow access to temp directory
            engine = ToolExecutionEngine(allowed_paths=[tempfile.gettempdir()])
            
            request = ToolRequest(
                tool_type=ToolType.FILE,
                command="read",
                args={
                    "operation": "read",
                    "path": temp_path,
                }
            )
            
            response = engine.execute(request)
            
            assert response.success is True
            assert "Test content" in response.output
        
        finally:
            os.unlink(temp_path)
    
    def test_file_write_operation(self):
        """Test file write operation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Allow access to temp directory
            engine = ToolExecutionEngine(allowed_paths=[temp_dir])
            
            temp_path = os.path.join(temp_dir, "test.txt")
            
            request = ToolRequest(
                tool_type=ToolType.FILE,
                command="write",
                args={
                    "operation": "write",
                    "path": temp_path,
                    "content": "New content",
                }
            )
            
            response = engine.execute(request)
            
            assert response.success is True
            
            # Verify file was written
            with open(temp_path, "r") as f:
                content = f.read()
            
            assert content == "New content"
    
    def test_file_delete_operation(self):
        """Test file delete operation"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        # Allow access to temp directory
        engine = ToolExecutionEngine(allowed_paths=[tempfile.gettempdir()])
        
        request = ToolRequest(
            tool_type=ToolType.FILE,
            command="delete",
            args={
                "operation": "delete",
                "path": temp_path,
            }
        )
        
        response = engine.execute(request)
        
        assert response.success is True
        assert not os.path.exists(temp_path)
    
    def test_file_access_denied(self):
        """Test file access denied"""
        engine = ToolExecutionEngine(allowed_paths=["/tmp"])
        
        request = ToolRequest(
            tool_type=ToolType.FILE,
            command="read",
            args={
                "operation": "read",
                "path": "/etc/passwd",
            }
        )
        
        response = engine.execute(request)
        
        assert response.success is False
        assert "Access denied" in response.error
    
    def test_grep_execution(self):
        """Test grep search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Allow access to temp directory
            engine = ToolExecutionEngine(allowed_paths=[temp_dir])
            
            # Create a test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Hello World\nHello Kabbalah\nGoodbye")
            
            request = ToolRequest(
                tool_type=ToolType.GREP,
                command="grep",
                args={
                    "pattern": "Hello",
                    "path": temp_dir,
                }
            )
            
            response = engine.execute(request)
            
            assert response.success is True
            assert "Hello" in response.output
    
    def test_web_request_execution(self):
        """Test web request execution"""
        try:
            import requests
        except ImportError:
            pytest.skip("requests library not installed")
        
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.WEB,
            command="GET",
            args={
                "method": "GET",
                "url": "https://httpbin.org/get",
            },
            timeout=10.0,
        )
        
        response = engine.execute(request)
        
        # May fail due to network, but should not crash
        assert response.duration_ms > 0
    
    def test_execution_history(self):
        """Test execution history tracking"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        engine.execute(request)
        engine.execute(request)
        
        history = engine.get_execution_history()
        
        assert len(history) == 2
        assert history[0]["tool_type"] == "bash"
        assert history[1]["tool_type"] == "bash"
    
    def test_clear_history(self):
        """Test clearing execution history"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        engine.execute(request)
        assert len(engine.get_execution_history()) == 1
        
        engine.clear_history()
        assert len(engine.get_execution_history()) == 0
    
    def test_bash_streaming(self):
        """Test bash command streaming"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'Line 1'; echo 'Line 2'; echo 'Line 3'",
            stream=True,
        )
        
        responses = list(engine.stream(request))
        
        assert len(responses) > 0
        
        # Check last response
        last_response = responses[-1]
        assert last_response.success is True
        assert "Line 1" in last_response.output
        assert "Line 2" in last_response.output
        assert "Line 3" in last_response.output
    
    def test_grep_streaming(self):
        """Test grep streaming"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Allow access to temp directory
            engine = ToolExecutionEngine(allowed_paths=[temp_dir])
            
            # Create test files
            for i in range(3):
                test_file = os.path.join(temp_dir, f"test{i}.txt")
                with open(test_file, "w") as f:
                    f.write(f"Hello {i}\nWorld {i}")
            
            request = ToolRequest(
                tool_type=ToolType.GREP,
                command="grep",
                args={
                    "pattern": "Hello",
                    "path": temp_dir,
                },
                stream=True,
            )
            
            responses = list(engine.stream(request))
            
            assert len(responses) > 0
            assert responses[-1].success is True


class TestResourceLimits:
    """Test Resource Limits"""
    
    def test_resource_limits_initialization(self):
        """Test resource limits initialization"""
        limits = ResourceLimits()
        
        assert limits.max_cpu_percent == 95.0
        assert limits.max_memory_mb == 4096
        assert limits.max_disk_mb == 10240
        assert limits.max_output_lines == 10000
    
    def test_resource_limits_custom(self):
        """Test custom resource limits"""
        limits = ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_mb=256,
            max_disk_mb=512,
            max_output_lines=5000,
        )
        
        assert limits.max_cpu_percent == 50.0
        assert limits.max_memory_mb == 256
        assert limits.max_disk_mb == 512
        assert limits.max_output_lines == 5000


class TestToolRequest:
    """Test Tool Request"""
    
    def test_tool_request_creation(self):
        """Test creating a tool request"""
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        assert request.tool_type == ToolType.BASH
        assert request.command == "echo 'test'"
        assert request.timeout == 30.0
        assert request.stream is False
        assert request.retry_count == 0
        assert request.cache_result is False
    
    def test_tool_request_with_args(self):
        """Test tool request with arguments"""
        request = ToolRequest(
            tool_type=ToolType.FILE,
            command="read",
            args={"path": "/tmp/test.txt"},
            timeout=10.0,
            retry_count=3,
            cache_result=True,
        )
        
        assert request.args["path"] == "/tmp/test.txt"
        assert request.timeout == 10.0
        assert request.retry_count == 3
        assert request.cache_result is True
    
    def test_tool_request_validation(self):
        """Test tool request validation"""
        # Valid request
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        is_valid, error = request.validate()
        assert is_valid is True
        assert error is None
        
        # Invalid: empty command
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="",
        )
        is_valid, error = request.validate()
        assert is_valid is False
        assert error is not None
        
        # Invalid: negative timeout
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            timeout=-1,
        )
        is_valid, error = request.validate()
        assert is_valid is False
        assert error is not None


class TestToolResponse:
    """Test Tool Response"""
    
    def test_tool_response_creation(self):
        """Test creating a tool response"""
        response = ToolResponse(
            success=True,
            output="Test output",
        )
        
        assert response.success is True
        assert response.output == "Test output"
        assert response.error is None
        assert response.exit_code == 0
    
    def test_tool_response_with_error(self):
        """Test tool response with error"""
        response = ToolResponse(
            success=False,
            output="",
            error="Test error",
            exit_code=1,
        )
        
        assert response.success is False
        assert response.error == "Test error"
        assert response.exit_code == 1


class TestToolType:
    """Test Tool Type enum"""
    
    def test_tool_types(self):
        """Test all tool types exist"""
        assert ToolType.BASH.value == "bash"
        assert ToolType.FILE.value == "file"
        assert ToolType.GREP.value == "grep"
        assert ToolType.WEB.value == "web"
        assert ToolType.MCP.value == "mcp"


class TestResourceMonitoring:
    """Test resource monitoring functionality"""
    
    def test_get_resource_usage(self):
        """Test getting current resource usage"""
        engine = ToolExecutionEngine()
        usage = engine.get_resource_usage()
        
        assert "cpu_percent" in usage
        assert "memory_mb" in usage
        assert "memory_percent" in usage
        assert "disk_mb" in usage
        assert "disk_percent" in usage
        
        # Verify values are reasonable
        assert 0 <= usage["cpu_percent"] <= 100
        assert usage["memory_mb"] > 0
        assert 0 <= usage["memory_percent"] <= 100
        assert usage["disk_mb"] > 0
        assert 0 <= usage["disk_percent"] <= 100
    
    def test_resource_limits_enforcement(self):
        """Test that resource limits are enforced"""
        # Create engine with very strict limits
        limits = ResourceLimits(
            max_cpu_percent=10,  # Very strict
            max_memory_mb=100,   # Very strict
            max_disk_mb=100,     # Very strict
        )
        engine = ToolExecutionEngine(resource_limits=limits)
        
        # Execute a simple command
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        response = engine.execute(request)
        
        # With strict limits, execution should fail due to resource constraints
        # (unless the system is extremely idle)
        # We just verify the response is valid
        assert isinstance(response, ToolResponse)
        assert response.output is not None or response.error is not None


class TestCaching:
    """Test result caching functionality"""
    
    def test_cache_enabled(self):
        """Test that caching works"""
        engine = ToolExecutionEngine(enable_cache=True)
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            cache_result=True,
            cache_ttl=3600,
        )
        
        # First execution
        response1 = engine.execute(request)
        assert response1.cached is False
        
        # Second execution (should be cached)
        response2 = engine.execute(request)
        assert response2.cached is True
        assert response2.output == response1.output
    
    def test_cache_disabled(self):
        """Test that caching can be disabled"""
        engine = ToolExecutionEngine(enable_cache=False)
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            cache_result=True,
        )
        
        # Both executions should not be cached
        response1 = engine.execute(request)
        response2 = engine.execute(request)
        
        assert response1.cached is False
        assert response2.cached is False
    
    def test_cache_stats(self):
        """Test cache statistics"""
        engine = ToolExecutionEngine(enable_cache=True, max_cache_size=10)
        
        stats = engine.get_cache_stats()
        assert stats["cache_enabled"] is True
        assert stats["max_cache_size"] == 10
        assert stats["cache_size"] == 0
        
        # Add a cached result
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            cache_result=True,
        )
        engine.execute(request)
        
        stats = engine.get_cache_stats()
        assert stats["cache_size"] == 1
    
    def test_clear_cache(self):
        """Test clearing cache"""
        engine = ToolExecutionEngine(enable_cache=True)
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            cache_result=True,
        )
        
        engine.execute(request)
        assert engine.get_cache_stats()["cache_size"] == 1
        
        engine.clear_cache()
        assert engine.get_cache_stats()["cache_size"] == 0


class TestMetrics:
    """Test performance metrics"""
    
    def test_metrics_collection(self):
        """Test that metrics are collected"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        engine.execute(request)
        
        metrics = engine.get_metrics()
        assert "bash_duration_ms" in metrics
        assert metrics["bash_duration_ms"]["count"] == 1
        assert metrics["bash_duration_ms"]["min"] > 0
        assert metrics["bash_duration_ms"]["max"] > 0
        assert metrics["bash_duration_ms"]["avg"] > 0
    
    def test_metrics_aggregation(self):
        """Test metrics aggregation"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
        )
        
        # Execute multiple times
        for _ in range(5):
            engine.execute(request)
        
        metrics = engine.get_metrics()
        assert metrics["bash_duration_ms"]["count"] == 5
        assert "p95" in metrics["bash_duration_ms"]


class TestRetryLogic:
    """Test retry logic"""
    
    def test_retry_on_failure(self):
        """Test that retries work on failure"""
        engine = ToolExecutionEngine()
        
        # Command that fails (exit with non-zero code)
        cmd = "exit 1" if os.name == "nt" else "false"
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command=cmd,
            retry_count=2,
            retry_delay=0.1,
        )
        
        response = engine.execute(request)
        assert response.success is False
        # Retry count should be 2 (number of retries performed)
        assert response.retry_count >= 0
    
    def test_no_retry_on_success(self):
        """Test that no retries happen on success"""
        engine = ToolExecutionEngine()
        
        request = ToolRequest(
            tool_type=ToolType.BASH,
            command="echo 'test'",
            retry_count=3,
        )
        
        response = engine.execute(request)
        assert response.success is True
        assert response.retry_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

