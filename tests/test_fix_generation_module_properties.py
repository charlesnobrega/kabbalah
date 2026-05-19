"""
Property-based tests for Fix Generation Module.

Tests correctness properties using Hypothesis:
- Property 8: Unique Fix Proposal Generation
- Property 9: Confidence Score Bounds
- Property 10: Manual Review Requirement
- Property 11: Fix Ranking by Confidence

Requirements: 3.1, 3.4, 3.8, 3.9
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import patch

from kabbalah.fix_generation_module import FixGenerationModule
from kabbalah.error_analysis_module import ErrorAnalysis
from kabbalah.self_healing_models import CodeChange, FixProposal, FixStatus


class TestFixGenerationModuleProperties:
    """Property-based tests for FixGenerationModule."""

    # Property 8: Unique Fix Proposal Generation
    @given(
        error_id=st.text(min_size=1, max_size=50),
        root_cause=st.text(min_size=1, max_size=200),
        confidence=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_unique_fix_id_generation(
        self, error_id, root_cause, confidence
    ):
        """
        **Validates: Requirements 3.1**

        Property 8: Unique Fix Proposal Generation
        For any generated fix proposals, each fix SHALL have a unique fix_id
        with no duplicates.
        """
        fix_generation_module = FixGenerationModule()
        
        error_analysis = ErrorAnalysis(
            error_id=error_id,
            root_cause=root_cause,
            suggested_fixes=["Fix 1"],
            affected_files=["src/test.py"],
            confidence_score=confidence,
            reasoning="Test reasoning",
            llm_model="llama2",
            analysis_time_ms=100.0,
        )

        code_change = CodeChange(
            file_path="src/test.py",
            original_content="x = 1",
            new_content="x = 2",
            line_start=1,
            line_end=1,
            diff="",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result1 = fix_generation_module.generate_fix(error_analysis)
                result2 = fix_generation_module.generate_fix(error_analysis)

        # Both results should have fixes
        assert len(result1.fixes) > 0
        assert len(result2.fixes) > 0

        # Fix IDs should be unique
        fix_id_1 = result1.fixes[0].fix_id
        fix_id_2 = result2.fixes[0].fix_id
        assert fix_id_1 != fix_id_2, "Fix IDs must be unique"

    # Property 9: Confidence Score Bounds
    @given(
        error_id=st.text(min_size=1, max_size=50),
        root_cause=st.text(min_size=1, max_size=200),
        base_confidence=st.floats(min_value=0.0, max_value=1.0),
        num_files=st.integers(min_value=1, max_value=10),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_confidence_score_bounds(
        self,
        error_id,
        root_cause,
        base_confidence,
        num_files,
    ):
        """
        **Validates: Requirements 3.4**

        Property 9: Confidence Score Bounds
        For any generated fix proposal, the confidence_score SHALL be between
        0.0 and 1.0 (inclusive).
        """
        fix_generation_module = FixGenerationModule()
        
        error_analysis = ErrorAnalysis(
            error_id=error_id,
            root_cause=root_cause,
            suggested_fixes=["Fix 1"],
            affected_files=[f"src/file{i}.py" for i in range(num_files)],
            confidence_score=base_confidence,
            reasoning="Test reasoning",
            llm_model="llama2",
            analysis_time_ms=100.0,
        )

        code_changes = [
            CodeChange(
                file_path=f"src/file{i}.py",
                original_content="x = 1",
                new_content="x = 2",
                line_start=1,
                line_end=1,
                diff="",
            )
            for i in range(num_files)
        ]

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=code_changes
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result = fix_generation_module.generate_fix(error_analysis)

        if result.fixes:
            confidence = result.fixes[0].confidence_score
            assert (
                0.0 <= confidence <= 1.0
            ), f"Confidence {confidence} out of bounds [0.0, 1.0]"

    # Property 10: Manual Review Requirement
    @given(
        error_id=st.text(min_size=1, max_size=50),
        root_cause=st.text(min_size=1, max_size=200),
        confidence=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_manual_review_requirement(
        self, error_id, root_cause, confidence
    ):
        """
        **Validates: Requirements 3.8, 13.3**

        Property 10: Manual Review Requirement
        For any fix proposal with confidence_score < 0.5, the
        requires_manual_review flag SHALL be True.
        """
        fix_generation_module = FixGenerationModule()
        
        error_analysis = ErrorAnalysis(
            error_id=error_id,
            root_cause=root_cause,
            suggested_fixes=["Fix 1"],
            affected_files=["src/test.py"],
            confidence_score=confidence,
            reasoning="Test reasoning",
            llm_model="llama2",
            analysis_time_ms=100.0,
        )

        code_change = CodeChange(
            file_path="src/test.py",
            original_content="x = 1",
            new_content="x = 2",
            line_start=1,
            line_end=1,
            diff="",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result = fix_generation_module.generate_fix(error_analysis)

        if result.fixes:
            fix = result.fixes[0]
            if fix.confidence_score < 0.5:
                assert (
                    fix.requires_manual_review is True
                ), "Low confidence fixes must require manual review"

    # Property 11: Fix Ranking by Confidence
    @given(
        confidences=st.lists(
            st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=10
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_fix_ranking_by_confidence(
        self, confidences
    ):
        """
        **Validates: Requirements 3.9**

        Property 11: Fix Ranking by Confidence
        For any set of multiple fix proposals for the same error, when ranked,
        the fixes SHALL be ordered by confidence_score in descending order.
        """
        fix_generation_module = FixGenerationModule()
        
        fixes = [
            FixProposal(
                fix_id=f"fix-{i}",
                error_id="err-001",
                description=f"Fix {i}",
                code_changes=[],
                confidence_score=conf,
                reasoning="",
                affected_files=[],
                requires_manual_review=False,
            )
            for i, conf in enumerate(confidences)
        ]

        ranked = fix_generation_module.rank_fixes(fixes)

        # Check that fixes are sorted in descending order by confidence
        for i in range(len(ranked) - 1):
            assert (
                ranked[i].confidence_score >= ranked[i + 1].confidence_score
            ), "Fixes must be ranked by confidence in descending order"

    # Additional property: Confidence score calculation consistency
    @given(
        base_confidence=st.floats(min_value=0.0, max_value=1.0),
        num_files=st.integers(min_value=1, max_value=10),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_confidence_calculation_consistency(
        self, base_confidence, num_files
    ):
        """
        Property: Confidence Score Calculation Consistency
        For the same error analysis and code changes, the confidence score
        calculation should be deterministic and consistent.
        """
        fix_generation_module = FixGenerationModule()
        
        error_analysis = ErrorAnalysis(
            error_id="err-001",
            root_cause="Test error",
            suggested_fixes=["Fix 1"],
            affected_files=[f"src/file{i}.py" for i in range(num_files)],
            confidence_score=base_confidence,
            reasoning="Test reasoning",
            llm_model="llama2",
            analysis_time_ms=100.0,
        )

        code_changes = [
            CodeChange(
                file_path=f"src/file{i}.py",
                original_content="x = 1",
                new_content="x = 2",
                line_start=1,
                line_end=1,
                diff="",
            )
            for i in range(num_files)
        ]

        # Calculate confidence twice
        confidence1 = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes
        )
        confidence2 = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes
        )

        # Should be identical
        assert (
            confidence1 == confidence2
        ), "Confidence calculation must be deterministic"

    # Property: Syntax validation consistency
    @given(
        file_path=st.just("src/test.py"),
        valid_code=st.just("def test():\n    return True"),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_syntax_validation_consistency(
        self, file_path, valid_code
    ):
        """
        Property: Syntax Validation Consistency
        For the same file and code content, syntax validation should always
        return the same result.
        """
        fix_generation_module = FixGenerationModule()
        
        result1 = fix_generation_module.validate_syntax(file_path, valid_code)
        result2 = fix_generation_module.validate_syntax(file_path, valid_code)

        assert (
            result1 == result2
        ), "Syntax validation must be deterministic"

    # Property: Code change extraction consistency
    @given(
        suggested_fixes=st.lists(
            st.text(min_size=1, max_size=100), min_size=0, max_size=5
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_code_change_extraction_consistency(
        self, suggested_fixes
    ):
        """
        Property: Code Change Extraction Consistency
        For the same suggested fixes, code change extraction should always
        return the same result.
        """
        fix_generation_module = FixGenerationModule()
        
        changes1 = fix_generation_module.extract_code_changes(suggested_fixes)
        changes2 = fix_generation_module.extract_code_changes(suggested_fixes)

        assert len(changes1) == len(
            changes2
        ), "Code change extraction must be deterministic"

        for c1, c2 in zip(changes1, changes2):
            assert (
                c1.file_path == c2.file_path
            ), "Extracted file paths must be identical"
            assert (
                c1.new_content == c2.new_content
            ), "Extracted content must be identical"
