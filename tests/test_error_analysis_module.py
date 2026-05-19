"""
Unit tests for Error Analysis Module.

Tests error analysis functionality including:
- LLM response parsing
- Malformed response handling
- Learning database fallback
- Timeout handling
- Confidence score extraction

Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from kabbalah.error_analysis_module import (
    ErrorAnalysisModule,
    ErrorAnalysis,
    TimeoutException,
)
from kabbalah.llm_local_provider import LocalLLMConfig, LocalLLMProvider
from kabbalah.self_healing_models import (
    ErrorReport,
    ErrorSeverity,
    CodeChange,
    LearningEntry,
)


class TestErrorAnalysisModule:
    """Test suite for ErrorAnalysisModule."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = Mock(spec=LocalLLMProvider)
        provider.available = True
        provider.config = LocalLLMConfig()
        return provider

    @pytest.fixture
    def error_report(self):
        """Create a sample error report."""
        return ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid input value",
            severity=ErrorSeverity.HIGH,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={"trace_id": "trace-123", "request_id": "req-456"},
            stack_trace="Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('Invalid input')",
            file_path="src/test.py",
            line_number=10,
        )

    @pytest.fixture
    def learning_entry(self):
        """Create a sample learning entry."""
        code_change = CodeChange(
            file_path="src/test.py",
            original_content="x = invalid_value",
            new_content="x = validate_value(invalid_value)",
            line_start=10,
            line_end=10,
            diff="- x = invalid_value\n+ x = validate_value(invalid_value)",
        )

        return LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError",
            error_type="ValueError",
            error_message_pattern="Invalid input*",
            fix_description="Add input validation",
            code_changes=[code_change],
            reasoning="Input validation prevents invalid values",
            confidence_score=0.85,
            usage_count=5,
            success_count=4,
            failure_count=1,
            success_rate=0.8,
        )

    def test_initialization(self, mock_llm_provider):
        """Test ErrorAnalysisModule initialization."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        assert module.llm_provider == mock_llm_provider
        assert module.learning_database == []
        assert module.analysis_history == {}

    def test_initialization_with_learning_database(self, mock_llm_provider, learning_entry):
        """Test initialization with learning database."""
        learning_db = [learning_entry]
        module = ErrorAnalysisModule(
            llm_provider=mock_llm_provider, learning_database=learning_db
        )

        assert module.learning_database == learning_db

    def test_generate_analysis_prompt_basic(self, mock_llm_provider, error_report):
        """Test basic analysis prompt generation."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)
        prompt = module.generate_analysis_prompt(error_report)

        assert "ValueError" in prompt
        assert "Invalid input value" in prompt
        assert "Root_Orchestrator" in prompt
        assert "src/test.py:10" in prompt
        assert "ANALYSIS REQUIRED" in prompt
        assert "RESPONSE FORMAT" in prompt

    def test_generate_analysis_prompt_with_learning_context(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test analysis prompt generation with learning context."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)
        prompt = module.generate_analysis_prompt(error_report, [learning_entry])

        assert "SIMILAR PATTERNS FROM LEARNING DATABASE" in prompt
        assert "ValueError" in prompt
        assert "Add input validation" in prompt
        assert "80.0%" in prompt  # success rate

    def test_parse_llm_response_valid_json(self, mock_llm_provider):
        """Test parsing valid LLM response with JSON."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        response = """{
            "root_cause": "Missing input validation",
            "suggested_fixes": ["Add validation", "Use try-except"],
            "affected_files": ["src/test.py", "src/utils.py"],
            "confidence": 0.85,
            "reasoning": "Input validation prevents errors"
        }"""

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        assert root_cause == "Missing input validation"
        assert fixes == ["Add validation", "Use try-except"]
        assert files == ["src/test.py", "src/utils.py"]
        assert confidence == 0.85

    def test_parse_llm_response_with_text_before_json(self, mock_llm_provider):
        """Test parsing LLM response with text before JSON."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        response = """Let me analyze this error:

{
    "root_cause": "Missing validation",
    "suggested_fixes": ["Add check"],
    "affected_files": ["src/test.py"],
    "confidence": 0.75,
    "reasoning": "Validation needed"
}

This should fix the issue."""

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        assert root_cause == "Missing validation"
        assert fixes == ["Add check"]
        assert confidence == 0.75

    def test_parse_llm_response_confidence_bounds(self, mock_llm_provider):
        """Test confidence score is bounded to 0.0-1.0."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        # Test confidence > 1.0
        response = '{"root_cause": "test", "suggested_fixes": [], "affected_files": [], "confidence": 1.5}'
        _, _, _, confidence = module.parse_llm_response(response)
        assert confidence == 1.0

        # Test confidence < 0.0
        response = '{"root_cause": "test", "suggested_fixes": [], "affected_files": [], "confidence": -0.5}'
        _, _, _, confidence = module.parse_llm_response(response)
        assert confidence == 0.0

    def test_parse_llm_response_missing_fields(self, mock_llm_provider):
        """Test parsing response with missing optional fields."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        response = '{"root_cause": "test", "confidence": 0.5}'

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        assert root_cause == "test"
        assert fixes == []
        assert files == []
        assert confidence == 0.5

    def test_parse_llm_response_invalid_json(self, mock_llm_provider):
        """Test parsing invalid JSON raises exception."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        response = "This is not JSON at all"

        with pytest.raises(Exception, match="does not contain valid JSON"):
            module.parse_llm_response(response)

    def test_parse_llm_response_malformed_json(self, mock_llm_provider):
        """Test parsing malformed JSON raises exception."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        response = '{"root_cause": "test", "confidence": invalid}'

        with pytest.raises(Exception, match="Invalid JSON"):
            module.parse_llm_response(response)

    def test_analyze_error_with_llm_success(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test successful error analysis with LLM."""
        module = ErrorAnalysisModule(
            llm_provider=mock_llm_provider, learning_database=[learning_entry]
        )

        llm_response = """{
            "root_cause": "Missing input validation",
            "suggested_fixes": ["Add validation"],
            "affected_files": ["src/test.py"],
            "confidence": 0.85,
            "reasoning": "Input validation prevents errors"
        }"""

        mock_llm_provider.analyze.return_value = llm_response

        analysis = module.analyze_error(error_report)

        assert analysis.error_id == "err-001"
        assert analysis.root_cause == "Missing input validation"
        assert analysis.suggested_fixes == ["Add validation"]
        assert analysis.affected_files == ["src/test.py"]
        assert analysis.confidence_score == 0.85
        assert analysis.llm_model == "llama2"
        assert not analysis.used_learning_database
        assert analysis.analysis_time_ms >= 0  # Can be 0 for very fast execution

    def test_analyze_error_llm_unavailable_fallback(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test fallback to learning database when LLM unavailable."""
        mock_llm_provider.available = False
        module = ErrorAnalysisModule(
            llm_provider=mock_llm_provider, learning_database=[learning_entry]
        )

        analysis = module.analyze_error(error_report, learning_context=[learning_entry])

        assert analysis.error_id == "err-001"
        assert analysis.llm_model == "learning_database"
        assert analysis.used_learning_database
        assert analysis.confidence_score > 0

    def test_analyze_error_llm_timeout_fallback(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test fallback to learning database on LLM timeout."""
        module = ErrorAnalysisModule(
            llm_provider=mock_llm_provider, learning_database=[learning_entry]
        )

        mock_llm_provider.analyze.side_effect = TimeoutException("Timeout")

        analysis = module.analyze_error(error_report, learning_context=[learning_entry])

        assert analysis.error_id == "err-001"
        assert analysis.used_learning_database

    def test_analyze_error_llm_exception_fallback(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test fallback to learning database on LLM exception."""
        module = ErrorAnalysisModule(
            llm_provider=mock_llm_provider, learning_database=[learning_entry]
        )

        mock_llm_provider.analyze.side_effect = Exception("LLM error")

        analysis = module.analyze_error(error_report, learning_context=[learning_entry])

        assert analysis.error_id == "err-001"
        assert analysis.used_learning_database

    def test_analyze_error_malformed_llm_response(
        self, mock_llm_provider, error_report
    ):
        """Test handling of malformed LLM response."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        mock_llm_provider.analyze.return_value = "This is not JSON"

        analysis = module.analyze_error(error_report)

        assert analysis.error_id == "err-001"
        assert analysis.confidence_score == 0.2  # Low confidence for malformed response
        assert "Unable to parse" in analysis.root_cause

    def test_analyze_error_empty_llm_response(self, mock_llm_provider, error_report):
        """Test handling of empty LLM response."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        mock_llm_provider.analyze.return_value = ""

        # Should fall back to learning database instead of raising exception
        analysis = module.analyze_error(error_report)

        assert analysis.error_id == "err-001"
        assert analysis.used_learning_database
        assert analysis.confidence_score == 0.1  # Low confidence for no patterns

    def test_analyze_error_with_learning_context(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test error analysis with learning context."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        llm_response = """{
            "root_cause": "Missing validation",
            "suggested_fixes": ["Add check"],
            "affected_files": ["src/test.py"],
            "confidence": 0.9,
            "reasoning": "Based on similar pattern"
        }"""

        mock_llm_provider.analyze.return_value = llm_response

        analysis = module.analyze_error(
            error_report, learning_context=[learning_entry]
        )

        assert analysis.confidence_score == 0.9
        assert "similar pattern" in analysis.reasoning.lower()

    def test_analyze_error_stores_in_history(
        self, mock_llm_provider, error_report
    ):
        """Test that analysis is stored in history."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        llm_response = """{
            "root_cause": "test",
            "suggested_fixes": [],
            "affected_files": [],
            "confidence": 0.5,
            "reasoning": "test"
        }"""

        mock_llm_provider.analyze.return_value = llm_response

        analysis = module.analyze_error(error_report)

        assert error_report.error_id in module.analysis_history
        assert module.analysis_history[error_report.error_id] == analysis

    def test_analyze_with_learning_database_no_context(
        self, mock_llm_provider, error_report
    ):
        """Test learning database analysis with no context."""
        mock_llm_provider.available = False
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        analysis = module.analyze_error(error_report)

        assert analysis.error_id == "err-001"
        assert analysis.confidence_score == 0.1
        assert "No similar patterns" in analysis.root_cause

    def test_analyze_with_learning_database_with_context(
        self, mock_llm_provider, error_report, learning_entry
    ):
        """Test learning database analysis with context."""
        mock_llm_provider.available = False
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        analysis = module.analyze_error(error_report, learning_context=[learning_entry])

        assert analysis.error_id == "err-001"
        assert analysis.root_cause == learning_entry.reasoning
        assert analysis.suggested_fixes == [learning_entry.fix_description]
        assert "src/test.py" in analysis.affected_files
        assert analysis.confidence_score == learning_entry.success_rate * 0.9

    def test_get_analysis_history(self, mock_llm_provider, error_report):
        """Test retrieving analysis history."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        llm_response = """{
            "root_cause": "test",
            "suggested_fixes": [],
            "affected_files": [],
            "confidence": 0.5,
            "reasoning": "test"
        }"""

        mock_llm_provider.analyze.return_value = llm_response

        module.analyze_error(error_report)

        history = module.get_analysis_history()

        assert len(history) == 1
        assert error_report.error_id in history

    def test_clear_analysis_history(self, mock_llm_provider, error_report):
        """Test clearing analysis history."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        llm_response = """{
            "root_cause": "test",
            "suggested_fixes": [],
            "affected_files": [],
            "confidence": 0.5,
            "reasoning": "test"
        }"""

        mock_llm_provider.analyze.return_value = llm_response

        module.analyze_error(error_report)
        assert len(module.analysis_history) > 0

        module.clear_analysis_history()
        assert len(module.analysis_history) == 0

    def test_set_learning_database(self, mock_llm_provider, learning_entry):
        """Test setting learning database."""
        module = ErrorAnalysisModule(llm_provider=mock_llm_provider)

        assert module.learning_database == []

        learning_db = [learning_entry]
        module.set_learning_database(learning_db)

        assert module.learning_database == learning_db

    def test_error_analysis_dataclass(self):
        """Test ErrorAnalysis dataclass creation."""
        analysis = ErrorAnalysis(
            error_id="err-001",
            root_cause="Missing validation",
            suggested_fixes=["Add check"],
            affected_files=["src/test.py"],
            confidence_score=0.85,
            reasoning="Input validation prevents errors",
            llm_model="llama2",
            analysis_time_ms=150.5,
            used_learning_database=False,
        )

        assert analysis.error_id == "err-001"
        assert analysis.root_cause == "Missing validation"
        assert analysis.confidence_score == 0.85
        assert analysis.analysis_time_ms == 150.5
        assert not analysis.used_learning_database
        assert isinstance(analysis.timestamp, datetime)

    def test_timeout_exception(self):
        """Test TimeoutException."""
        exc = TimeoutException("Test timeout")
        assert str(exc) == "Test timeout"
        assert isinstance(exc, Exception)


class TestErrorAnalysisIntegration:
    """Integration tests for ErrorAnalysisModule."""

    def test_full_analysis_pipeline_with_llm(self):
        """Test complete analysis pipeline with LLM."""
        # Create mock LLM provider
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        # Create error report
        error_report = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid input",
            severity=ErrorSeverity.HIGH,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={"trace_id": "trace-123"},
            stack_trace="Traceback...",
            file_path="src/test.py",
            line_number=10,
        )

        # Create module
        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Mock LLM response
        llm_response = """{
            "root_cause": "Missing input validation",
            "suggested_fixes": ["Add validation check"],
            "affected_files": ["src/test.py"],
            "confidence": 0.85,
            "reasoning": "Input validation prevents errors"
        }"""

        mock_provider.analyze.return_value = llm_response

        # Analyze error
        analysis = module.analyze_error(error_report)

        # Verify analysis
        assert analysis.error_id == "err-001"
        assert analysis.confidence_score == 0.85
        assert not analysis.used_learning_database

    def test_full_analysis_pipeline_with_learning_database(self):
        """Test complete analysis pipeline with learning database."""
        # Create mock LLM provider (unavailable)
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = False

        # Create learning entry
        code_change = CodeChange(
            file_path="src/test.py",
            original_content="x = value",
            new_content="x = validate(value)",
            line_start=10,
            line_end=10,
            diff="- x = value\n+ x = validate(value)",
        )

        learning_entry = LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError",
            error_type="ValueError",
            error_message_pattern="Invalid*",
            fix_description="Add validation",
            code_changes=[code_change],
            reasoning="Validation prevents errors",
            confidence_score=0.85,
            usage_count=5,
            success_count=4,
            failure_count=1,
            success_rate=0.8,
        )

        # Create error report
        error_report = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid input",
            severity=ErrorSeverity.HIGH,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={"trace_id": "trace-123"},
            stack_trace="Traceback...",
            file_path="src/test.py",
            line_number=10,
        )

        # Create module with learning database
        module = ErrorAnalysisModule(
            llm_provider=mock_provider, learning_database=[learning_entry]
        )

        # Analyze error
        analysis = module.analyze_error(error_report, learning_context=[learning_entry])

        # Verify analysis
        assert analysis.error_id == "err-001"
        assert analysis.used_learning_database
        assert analysis.confidence_score == 0.8 * 0.9  # success_rate * 0.9
