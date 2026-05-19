"""
Property-based tests for Error Analysis Module.

Tests correctness properties using Hypothesis:
- Property 5: LLM Response Parsing - Valid LLM responses parsed correctly
- Property 7: Malformed LLM Response Handling - Malformed responses return low confidence

Requirements: 2.3, 2.5
"""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest
from hypothesis import given, strategies as st, assume

from kabbalah.error_analysis_module import ErrorAnalysisModule, ErrorAnalysis
from kabbalah.llm_local_provider import LocalLLMConfig, LocalLLMProvider
from kabbalah.self_healing_models import (
    ErrorReport,
    ErrorSeverity,
    CodeChange,
    LearningEntry,
)


# Strategies for generating test data
@st.composite
def error_reports(draw):
    """Generate valid ErrorReport instances."""
    return ErrorReport(
        error_id=draw(st.text(min_size=1, max_size=50)),
        error_type=draw(st.sampled_from(["ValueError", "TypeError", "RuntimeError"])),
        message=draw(st.text(min_size=1, max_size=200)),
        severity=draw(st.sampled_from(list(ErrorSeverity))),
        timestamp=datetime.now(),
        component=draw(
            st.sampled_from(
                [
                    "Root_Orchestrator",
                    "Domain_Orchestrator",
                    "Leaf_Node",
                    "Intake_Node",
                    "Synthesizer",
                ]
            )
        ),
        context={"trace_id": draw(st.text(min_size=1, max_size=50))},
        stack_trace=draw(st.text(min_size=1, max_size=500)),
        file_path=draw(st.text(min_size=1, max_size=100)),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
    )


@st.composite
def valid_llm_responses(draw):
    """Generate valid LLM response JSON."""
    root_cause = draw(st.text(min_size=1, max_size=200))
    num_fixes = draw(st.integers(min_value=1, max_value=3))
    suggested_fixes = [
        draw(st.text(min_size=1, max_size=100)) for _ in range(num_fixes)
    ]
    num_files = draw(st.integers(min_value=1, max_value=5))
    affected_files = [
        draw(st.text(min_size=1, max_size=50)) for _ in range(num_files)
    ]
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    reasoning = draw(st.text(min_size=1, max_size=200))

    response_dict = {
        "root_cause": root_cause,
        "suggested_fixes": suggested_fixes,
        "affected_files": affected_files,
        "confidence": confidence,
        "reasoning": reasoning,
    }

    return json.dumps(response_dict)


@st.composite
def malformed_llm_responses(draw):
    """Generate malformed LLM responses."""
    malformation_type = draw(
        st.sampled_from(
            [
                "no_json",
                "invalid_json",
                "missing_fields",
                "wrong_types",
                "empty",
            ]
        )
    )

    if malformation_type == "no_json":
        return draw(st.text(min_size=1, max_size=200))
    elif malformation_type == "invalid_json":
        return "{invalid json content"
    elif malformation_type == "missing_fields":
        return '{"root_cause": "test"}'
    elif malformation_type == "wrong_types":
        return '{"root_cause": 123, "confidence": "high"}'
    elif malformation_type == "empty":
        return ""
    else:
        return "???"


class TestErrorAnalysisProperties:
    """Property-based tests for ErrorAnalysisModule."""

    @given(valid_llm_responses())
    def test_property_5_llm_response_parsing(self, llm_response):
        """
        Property 5: LLM Response Parsing
        
        For any valid LLM response containing root cause analysis, suggested fixes,
        affected files, and confidence score, the Error_Analysis_Module SHALL
        correctly parse and extract all fields.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Parse the response
        root_cause, fixes, files, confidence = module.parse_llm_response(llm_response)

        # Verify all fields are extracted
        assert isinstance(root_cause, str)
        assert len(root_cause) > 0

        assert isinstance(fixes, list)
        assert len(fixes) > 0
        assert all(isinstance(f, str) for f in fixes)

        assert isinstance(files, list)
        assert len(files) > 0
        assert all(isinstance(f, str) for f in files)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    @given(malformed_llm_responses())
    def test_property_7_malformed_response_handling(self, malformed_response):
        """
        Property 7: Malformed LLM Response Handling
        
        For any malformed LLM response, the Error_Analysis_Module SHALL return
        a default analysis with low confidence (< 0.5) rather than crashing.

        **Validates: Requirements 2.5**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        error_report = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Test error",
            severity=ErrorSeverity.HIGH,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=1,
        )

        module = ErrorAnalysisModule(llm_provider=mock_provider)
        mock_provider.analyze.return_value = malformed_response

        # Should not raise exception
        analysis = module.analyze_error(error_report)

        # Should return analysis with low confidence
        assert isinstance(analysis, ErrorAnalysis)
        assert analysis.error_id == "err-001"
        # Confidence should be low for malformed responses (or use learning database fallback)
        assert analysis.confidence_score <= 0.5

    @given(error_reports())
    def test_property_5_parsing_preserves_data_integrity(self, error_report):
        """
        Property 5 Extended: Parsing preserves data integrity
        
        For any valid LLM response, parsing SHALL preserve all data without
        corruption or loss.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Create a valid response
        response = json.dumps(
            {
                "root_cause": "Test root cause",
                "suggested_fixes": ["Fix 1", "Fix 2"],
                "affected_files": ["file1.py", "file2.py"],
                "confidence": 0.75,
                "reasoning": "Test reasoning",
            }
        )

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        # Verify data integrity
        assert root_cause == "Test root cause"
        assert fixes == ["Fix 1", "Fix 2"]
        assert files == ["file1.py", "file2.py"]
        assert confidence == 0.75

    @given(st.floats(min_value=-10.0, max_value=10.0))
    def test_property_9_confidence_score_bounds(self, confidence_value):
        """
        Property 9: Confidence Score Bounds
        
        For any generated fix proposal, the confidence_score SHALL be between
        0.0 and 1.0 (inclusive).

        **Validates: Requirements 3.4**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Create response with arbitrary confidence
        response = json.dumps(
            {
                "root_cause": "test",
                "suggested_fixes": [],
                "affected_files": [],
                "confidence": confidence_value,
                "reasoning": "test",
            }
        )

        _, _, _, parsed_confidence = module.parse_llm_response(response)

        # Verify bounds
        assert 0.0 <= parsed_confidence <= 1.0

    @given(valid_llm_responses())
    def test_property_5_parsing_idempotent(self, llm_response):
        """
        Property 5 Extended: Parsing is idempotent
        
        For any valid LLM response, parsing the same response multiple times
        SHALL produce identical results.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Parse multiple times
        result1 = module.parse_llm_response(llm_response)
        result2 = module.parse_llm_response(llm_response)
        result3 = module.parse_llm_response(llm_response)

        # Results should be identical
        assert result1 == result2
        assert result2 == result3

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5))
    def test_property_5_parsing_handles_empty_lists(self, empty_list):
        """
        Property 5 Extended: Parsing handles empty lists
        
        For any LLM response with empty lists, parsing SHALL handle gracefully.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        response = json.dumps(
            {
                "root_cause": "test",
                "suggested_fixes": [],
                "affected_files": [],
                "confidence": 0.5,
                "reasoning": "test",
            }
        )

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        assert isinstance(fixes, list)
        assert isinstance(files, list)
        assert len(fixes) == 0
        assert len(files) == 0

    @given(error_reports(), valid_llm_responses())
    def test_property_5_analysis_with_valid_response(self, error_report, llm_response):
        """
        Property 5 Extended: Analysis with valid response
        
        For any error report and valid LLM response, analysis SHALL complete
        successfully and return valid ErrorAnalysis.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()
        mock_provider.analyze.return_value = llm_response

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        analysis = module.analyze_error(error_report)

        assert isinstance(analysis, ErrorAnalysis)
        assert analysis.error_id == error_report.error_id
        assert 0.0 <= analysis.confidence_score <= 1.0
        assert analysis.analysis_time_ms >= 0

    @given(error_reports())
    def test_property_7_malformed_response_returns_low_confidence(self, error_report):
        """
        Property 7 Extended: Malformed response returns low confidence
        
        For any error report with malformed LLM response, analysis SHALL
        return with confidence < 0.3.

        **Validates: Requirements 2.5**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()
        mock_provider.analyze.return_value = "This is not valid JSON"

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        analysis = module.analyze_error(error_report)

        assert analysis.confidence_score < 0.3

    @given(error_reports())
    def test_property_7_malformed_response_no_crash(self, error_report):
        """
        Property 7 Extended: Malformed response doesn't crash
        
        For any error report with malformed LLM response, analysis SHALL
        complete without raising exception.

        **Validates: Requirements 2.5**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()
        mock_provider.analyze.return_value = "Invalid response {{{{"

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        # Should not raise exception
        try:
            analysis = module.analyze_error(error_report)
            assert isinstance(analysis, ErrorAnalysis)
        except Exception as e:
            pytest.fail(f"Analysis raised exception: {str(e)}")

    @given(st.text(min_size=1, max_size=100))
    def test_property_5_parsing_with_extra_fields(self, extra_field_value):
        """
        Property 5 Extended: Parsing ignores extra fields
        
        For any LLM response with extra fields, parsing SHALL ignore them
        and extract only required fields.

        **Validates: Requirements 2.3**
        """
        mock_provider = Mock(spec=LocalLLMProvider)
        mock_provider.available = True
        mock_provider.config = LocalLLMConfig()

        module = ErrorAnalysisModule(llm_provider=mock_provider)

        response = json.dumps(
            {
                "root_cause": "test",
                "suggested_fixes": ["fix"],
                "affected_files": ["file.py"],
                "confidence": 0.5,
                "reasoning": "test",
                "extra_field": extra_field_value,
                "another_extra": 12345,
            }
        )

        root_cause, fixes, files, confidence = module.parse_llm_response(response)

        # Should parse successfully despite extra fields
        assert root_cause == "test"
        assert fixes == ["fix"]
        assert files == ["file.py"]
        assert confidence == 0.5
