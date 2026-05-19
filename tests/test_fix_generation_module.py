"""
Unit tests for Fix Generation Module.

Tests fix generation functionality including:
- Fix proposal generation from error analysis
- Code change extraction from suggested fixes
- Syntax validation for Python code
- Confidence score calculation
- Fix ranking by confidence

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from kabbalah.fix_generation_module import (
    FixGenerationModule,
    FixGenerationResult,
)
from kabbalah.error_analysis_module import ErrorAnalysis
from kabbalah.self_healing_models import (
    CodeChange,
    FixProposal,
    FixStatus,
    LearningEntry,
)


class TestFixGenerationModule:
    """Test suite for FixGenerationModule."""

    @pytest.fixture
    def fix_generation_module(self):
        """Create a FixGenerationModule instance."""
        return FixGenerationModule()

    @pytest.fixture
    def error_analysis(self):
        """Create a sample error analysis."""
        return ErrorAnalysis(
            error_id="err-001",
            root_cause="Invalid input validation in user registration",
            suggested_fixes=[
                "Add input validation for email field",
                "Implement password strength check",
            ],
            affected_files=["src/auth/registration.py", "src/auth/validators.py"],
            confidence_score=0.85,
            reasoning="Error occurs due to missing input validation",
            llm_model="llama2",
            analysis_time_ms=150.0,
            used_learning_database=False,
        )

    @pytest.fixture
    def learning_entry(self):
        """Create a sample learning entry."""
        code_change = CodeChange(
            file_path="src/auth/validators.py",
            original_content="def validate_email(email):\n    return True",
            new_content="def validate_email(email):\n    import re\n    return re.match(r'^[^@]+@[^@]+\\.[^@]+$', email) is not None",
            line_start=1,
            line_end=2,
            diff="- def validate_email(email):\n-     return True\n+ def validate_email(email):\n+     import re\n+     return re.match(r'^[^@]+@[^@]+\\.[^@]+$', email) is not None",
        )

        return LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError",
            error_type="ValueError",
            error_message_pattern="Invalid email*",
            fix_description="Add email validation",
            code_changes=[code_change],
            reasoning="Email validation prevents invalid emails",
            confidence_score=0.9,
            usage_count=10,
            success_count=9,
            failure_count=1,
            success_rate=0.9,
        )

    def test_initialization(self, fix_generation_module):
        """Test FixGenerationModule initialization."""
        assert fix_generation_module.generation_history == {}

    def test_generate_fix_basic(self, fix_generation_module, error_analysis):
        """Test basic fix generation from error analysis."""
        # Mock the extract_code_changes to return valid changes
        code_change = CodeChange(
            file_path="src/auth/registration.py",
            original_content="email = request.get('email')",
            new_content="email = validate_email(request.get('email'))",
            line_start=10,
            line_end=10,
            diff="- email = request.get('email')\n+ email = validate_email(request.get('email'))",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result = fix_generation_module.generate_fix(error_analysis)

        assert isinstance(result, FixGenerationResult)
        assert len(result.fixes) == 1
        assert result.primary_fix is not None
        assert result.primary_fix.error_id == "err-001"
        assert result.primary_fix.status == FixStatus.PENDING
        assert result.generation_time_ms >= 0  # Can be 0 for very fast operations

    def test_generate_fix_with_learning_context(
        self, fix_generation_module, error_analysis, learning_entry
    ):
        """Test fix generation with learning context."""
        code_change = CodeChange(
            file_path="src/auth/registration.py",
            original_content="email = request.get('email')",
            new_content="email = validate_email(request.get('email'))",
            line_start=10,
            line_end=10,
            diff="- email = request.get('email')\n+ email = validate_email(request.get('email'))",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result = fix_generation_module.generate_fix(
                    error_analysis, learning_context=[learning_entry]
                )

        assert len(result.fixes) == 1
        # Confidence should be boosted by learning context
        assert result.primary_fix.confidence_score > error_analysis.confidence_score

    def test_generate_fix_no_code_changes(self, fix_generation_module, error_analysis):
        """Test fix generation when no code changes can be extracted."""
        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[]
        ):
            result = fix_generation_module.generate_fix(error_analysis)

        assert len(result.fixes) == 0
        assert result.primary_fix is None
        assert len(result.errors) > 0

    def test_generate_fix_syntax_validation_failure(
        self, fix_generation_module, error_analysis
    ):
        """Test fix generation with syntax validation failure."""
        code_change = CodeChange(
            file_path="src/auth/registration.py",
            original_content="email = request.get('email')",
            new_content="email = request.get('email'  # Missing closing paren",
            line_start=10,
            line_end=10,
            diff="",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=False
            ):
                result = fix_generation_module.generate_fix(error_analysis)

        # Should still generate fix but with errors recorded
        assert len(result.errors) > 0

    def test_generate_fix_requires_manual_review_low_confidence(
        self, fix_generation_module
    ):
        """Test that low confidence fixes require manual review."""
        error_analysis = ErrorAnalysis(
            error_id="err-002",
            root_cause="Unknown error",
            suggested_fixes=["Try something"],
            affected_files=["src/test.py"],
            confidence_score=0.3,  # Low confidence
            reasoning="Not sure about this fix",
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

        assert result.primary_fix.requires_manual_review is True

    def test_generate_fix_requires_manual_review_many_files(
        self, fix_generation_module, error_analysis
    ):
        """Test that fixes affecting many files require manual review."""
        code_changes = [
            CodeChange(
                file_path=f"src/file{i}.py",
                original_content="x = 1",
                new_content="x = 2",
                line_start=1,
                line_end=1,
                diff="",
            )
            for i in range(6)  # 6 files
        ]

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=code_changes
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result = fix_generation_module.generate_fix(error_analysis)

        assert result.primary_fix.requires_manual_review is True

    def test_extract_code_changes_from_code_block(self, fix_generation_module):
        """Test extracting code changes from code block format."""
        suggested_fixes = [
            """File: src/auth/registration.py
```python
def validate_email(email):
    import re
    return re.match(r'^[^@]+@[^@]+\\.[^@]+$', email) is not None
```"""
        ]

        changes = fix_generation_module.extract_code_changes(suggested_fixes)

        assert len(changes) == 1
        assert changes[0].file_path == "src/auth/registration.py"
        assert "validate_email" in changes[0].new_content
        assert "import re" in changes[0].new_content

    def test_extract_code_changes_from_file_marker(self, fix_generation_module):
        """Test extracting code changes from file marker format."""
        suggested_fixes = [
            """file: src/test.py
new content:
def test_function():
    return True"""
        ]

        changes = fix_generation_module.extract_code_changes(suggested_fixes)

        assert len(changes) == 1
        assert changes[0].file_path == "src/test.py"
        assert "test_function" in changes[0].new_content

    def test_extract_code_changes_empty_list(self, fix_generation_module):
        """Test extracting code changes from empty list."""
        changes = fix_generation_module.extract_code_changes([])
        assert len(changes) == 0

    def test_extract_code_changes_malformed_input(self, fix_generation_module):
        """Test extracting code changes from malformed input."""
        suggested_fixes = [
            "This is just plain text without any code blocks or file markers"
        ]

        changes = fix_generation_module.extract_code_changes(suggested_fixes)

        # Should handle gracefully and return empty list
        assert len(changes) == 0

    def test_validate_syntax_valid_python(self, fix_generation_module):
        """Test syntax validation for valid Python code."""
        valid_code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        assert fix_generation_module.validate_syntax("src/test.py", valid_code) is True

    def test_validate_syntax_invalid_python(self, fix_generation_module):
        """Test syntax validation for invalid Python code."""
        invalid_code = """
def hello_world(
    print("Hello, World!")
"""
        assert (
            fix_generation_module.validate_syntax("src/test.py", invalid_code) is False
        )

    def test_validate_syntax_non_python_file(self, fix_generation_module):
        """Test syntax validation for non-Python files."""
        # Non-Python files should pass validation (skipped)
        assert (
            fix_generation_module.validate_syntax("src/test.js", "invalid code")
            is True
        )

    def test_validate_syntax_complex_code(self, fix_generation_module):
        """Test syntax validation for complex Python code."""
        complex_code = """
class MyClass:
    def __init__(self, value):
        self.value = value
    
    def method(self):
        try:
            return self.value * 2
        except Exception as e:
            print(f"Error: {e}")
            return None
"""
        assert (
            fix_generation_module.validate_syntax("src/test.py", complex_code) is True
        )

    def test_rank_fixes_by_confidence(self, fix_generation_module):
        """Test ranking fixes by confidence score."""
        fixes = [
            FixProposal(
                fix_id="fix-1",
                error_id="err-001",
                description="Fix 1",
                code_changes=[],
                confidence_score=0.5,
                reasoning="",
                affected_files=[],
                requires_manual_review=False,
            ),
            FixProposal(
                fix_id="fix-2",
                error_id="err-001",
                description="Fix 2",
                code_changes=[],
                confidence_score=0.9,
                reasoning="",
                affected_files=[],
                requires_manual_review=False,
            ),
            FixProposal(
                fix_id="fix-3",
                error_id="err-001",
                description="Fix 3",
                code_changes=[],
                confidence_score=0.7,
                reasoning="",
                affected_files=[],
                requires_manual_review=False,
            ),
        ]

        ranked = fix_generation_module.rank_fixes(fixes)

        assert len(ranked) == 3
        assert ranked[0].fix_id == "fix-2"  # 0.9
        assert ranked[1].fix_id == "fix-3"  # 0.7
        assert ranked[2].fix_id == "fix-1"  # 0.5

    def test_rank_fixes_empty_list(self, fix_generation_module):
        """Test ranking empty list of fixes."""
        ranked = fix_generation_module.rank_fixes([])
        assert len(ranked) == 0

    def test_rank_fixes_single_fix(self, fix_generation_module):
        """Test ranking single fix."""
        fix = FixProposal(
            fix_id="fix-1",
            error_id="err-001",
            description="Fix 1",
            code_changes=[],
            confidence_score=0.8,
            reasoning="",
            affected_files=[],
            requires_manual_review=False,
        )

        ranked = fix_generation_module.rank_fixes([fix])

        assert len(ranked) == 1
        assert ranked[0].fix_id == "fix-1"

    def test_calculate_confidence_score_base(self, fix_generation_module, error_analysis):
        """Test confidence score calculation with base score."""
        code_changes = [
            CodeChange(
                file_path="src/test.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            )
        ]

        confidence = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes
        )

        # Should be close to base confidence (0.85)
        assert 0.8 <= confidence <= 0.9

    def test_calculate_confidence_score_file_penalty(
        self, fix_generation_module, error_analysis
    ):
        """Test confidence score calculation with file count penalty."""
        code_changes = [
            CodeChange(
                file_path=f"src/file{i}.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            )
            for i in range(5)  # 5 files
        ]

        confidence = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes
        )

        # Should be penalized for multiple files
        assert confidence < error_analysis.confidence_score

    def test_calculate_confidence_score_learning_boost(
        self, fix_generation_module, error_analysis, learning_entry
    ):
        """Test confidence score calculation with learning database boost."""
        code_changes = [
            CodeChange(
                file_path="src/test.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            )
        ]

        confidence = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes, learning_context=[learning_entry]
        )

        # Should be boosted by learning context
        assert confidence > error_analysis.confidence_score

    def test_calculate_confidence_score_bounds(
        self, fix_generation_module, error_analysis
    ):
        """Test that confidence score stays within bounds."""
        code_changes = [
            CodeChange(
                file_path=f"src/file{i}.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            )
            for i in range(10)  # Many files
        ]

        confidence = fix_generation_module._calculate_confidence_score(
            error_analysis, code_changes
        )

        # Should be bounded between 0.0 and 1.0
        assert 0.0 <= confidence <= 1.0

    def test_generation_history(self, fix_generation_module, error_analysis):
        """Test generation history tracking."""
        code_change = CodeChange(
            file_path="src/test.py",
            original_content="",
            new_content="",
            line_start=0,
            line_end=0,
            diff="",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                result1 = fix_generation_module.generate_fix(error_analysis)

        history = fix_generation_module.get_generation_history()

        assert "err-001" in history
        assert history["err-001"] == result1

    def test_clear_generation_history(self, fix_generation_module, error_analysis):
        """Test clearing generation history."""
        code_change = CodeChange(
            file_path="src/test.py",
            original_content="",
            new_content="",
            line_start=0,
            line_end=0,
            diff="",
        )

        with patch.object(
            fix_generation_module, "extract_code_changes", return_value=[code_change]
        ):
            with patch.object(
                fix_generation_module, "validate_syntax", return_value=True
            ):
                fix_generation_module.generate_fix(error_analysis)

        assert len(fix_generation_module.generation_history) > 0

        fix_generation_module.clear_generation_history()

        assert len(fix_generation_module.generation_history) == 0

    def test_generate_fix_description(self, fix_generation_module):
        """Test fix description generation."""
        root_cause = "Missing input validation"
        code_changes = [
            CodeChange(
                file_path="src/auth.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            ),
            CodeChange(
                file_path="src/validators.py",
                original_content="",
                new_content="",
                line_start=0,
                line_end=0,
                diff="",
            ),
        ]

        description = fix_generation_module._generate_fix_description(
            root_cause, code_changes
        )

        assert "Missing input validation" in description
        assert "2 file(s)" in description
        assert "src/auth.py" in description
        assert "src/validators.py" in description
