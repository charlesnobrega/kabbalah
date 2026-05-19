"""
Unit tests for self-healing deployment system data models.

Tests verify that all enums and dataclasses can be instantiated correctly,
have proper type hints, default values work as expected, and docstrings
are present and clear.

Requirements: 1.3, 1.4, 1.5, 3.1, 4.1, 6.1, 6.2
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from src.kabbalah.self_healing_models import (
    ErrorSeverity,
    FixStatus,
    ErrorReport,
    CodeChange,
    FixProposal,
    Checkpoint,
    LearningEntry,
)


class TestErrorSeverityEnum:
    """Test ErrorSeverity enum definition and values."""

    def test_error_severity_has_all_required_values(self):
        """Verify ErrorSeverity enum has all five required severity levels."""
        assert hasattr(ErrorSeverity, "CRITICAL")
        assert hasattr(ErrorSeverity, "HIGH")
        assert hasattr(ErrorSeverity, "MEDIUM")
        assert hasattr(ErrorSeverity, "LOW")
        assert hasattr(ErrorSeverity, "INFO")

    def test_error_severity_values_are_strings(self):
        """Verify ErrorSeverity enum values are correct strings."""
        assert ErrorSeverity.CRITICAL.value == "CRITICAL"
        assert ErrorSeverity.HIGH.value == "HIGH"
        assert ErrorSeverity.MEDIUM.value == "MEDIUM"
        assert ErrorSeverity.LOW.value == "LOW"
        assert ErrorSeverity.INFO.value == "INFO"

    def test_error_severity_can_be_instantiated(self):
        """Verify ErrorSeverity enum members can be instantiated."""
        severity = ErrorSeverity.CRITICAL
        assert severity == ErrorSeverity.CRITICAL
        assert isinstance(severity, ErrorSeverity)

    def test_error_severity_comparison(self):
        """Verify ErrorSeverity enum members can be compared."""
        assert ErrorSeverity.CRITICAL != ErrorSeverity.HIGH
        assert ErrorSeverity.CRITICAL == ErrorSeverity.CRITICAL


class TestFixStatusEnum:
    """Test FixStatus enum definition and values."""

    def test_fix_status_has_all_required_values(self):
        """Verify FixStatus enum has all five required status values."""
        assert hasattr(FixStatus, "PENDING")
        assert hasattr(FixStatus, "APPLIED")
        assert hasattr(FixStatus, "VERIFIED")
        assert hasattr(FixStatus, "FAILED")
        assert hasattr(FixStatus, "REVERTED")

    def test_fix_status_values_are_strings(self):
        """Verify FixStatus enum values are correct strings."""
        assert FixStatus.PENDING.value == "PENDING"
        assert FixStatus.APPLIED.value == "APPLIED"
        assert FixStatus.VERIFIED.value == "VERIFIED"
        assert FixStatus.FAILED.value == "FAILED"
        assert FixStatus.REVERTED.value == "REVERTED"

    def test_fix_status_can_be_instantiated(self):
        """Verify FixStatus enum members can be instantiated."""
        status = FixStatus.PENDING
        assert status == FixStatus.PENDING
        assert isinstance(status, FixStatus)


class TestErrorReport:
    """Test ErrorReport dataclass."""

    def test_error_report_creation_with_all_fields(self):
        """Verify ErrorReport can be created with all required fields."""
        now = datetime.now()
        context = {"trace_id": "trace-123", "request_id": "req-456"}

        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid value provided",
            severity=ErrorSeverity.HIGH,
            timestamp=now,
            component="Root_Orchestrator",
            context=context,
            stack_trace="Traceback (most recent call last):\n  File...",
            file_path="src/kabbalah/root_orchestrator.py",
            line_number=42,
        )

        assert error.error_id == "err-001"
        assert error.error_type == "ValueError"
        assert error.message == "Invalid value provided"
        assert error.severity == ErrorSeverity.HIGH
        assert error.timestamp == now
        assert error.component == "Root_Orchestrator"
        assert error.context == context
        assert error.stack_trace == "Traceback (most recent call last):\n  File..."
        assert error.file_path == "src/kabbalah/root_orchestrator.py"
        assert error.line_number == 42

    def test_error_report_default_values(self):
        """Verify ErrorReport has correct default values."""
        now = datetime.now()
        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid value",
            severity=ErrorSeverity.MEDIUM,
            timestamp=now,
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=1,
        )

        assert error.occurrence_count == 1
        assert error.status == "DETECTED"

    def test_error_report_occurrence_count_increment(self):
        """Verify ErrorReport occurrence_count can be incremented."""
        now = datetime.now()
        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid value",
            severity=ErrorSeverity.MEDIUM,
            timestamp=now,
            component="Leaf_Node",
            context={},
            stack_trace="",
            file_path="test.py",
            line_number=1,
            occurrence_count=5,
        )

        assert error.occurrence_count == 5

    def test_error_report_has_docstring(self):
        """Verify ErrorReport has a docstring."""
        assert ErrorReport.__doc__ is not None
        assert len(ErrorReport.__doc__) > 0


class TestCodeChange:
    """Test CodeChange dataclass."""

    def test_code_change_creation(self):
        """Verify CodeChange can be created with all fields."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="def foo():\n    pass",
            new_content="def foo():\n    return 42",
            line_start=1,
            line_end=2,
            diff="--- a/src/module.py\n+++ b/src/module.py\n@@ -1,2 +1,2 @@",
        )

        assert change.file_path == "src/module.py"
        assert change.original_content == "def foo():\n    pass"
        assert change.new_content == "def foo():\n    return 42"
        assert change.line_start == 1
        assert change.line_end == 2
        assert change.diff.startswith("---")

    def test_code_change_has_docstring(self):
        """Verify CodeChange has a docstring."""
        assert CodeChange.__doc__ is not None
        assert len(CodeChange.__doc__) > 0


class TestFixProposal:
    """Test FixProposal dataclass."""

    def test_fix_proposal_creation_with_all_fields(self):
        """Verify FixProposal can be created with all required fields."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="def foo():\n    pass",
            new_content="def foo():\n    return 42",
            line_start=1,
            line_end=2,
            diff="--- a/src/module.py\n+++ b/src/module.py",
        )

        proposal = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Add return statement to foo()",
            code_changes=[change],
            confidence_score=0.85,
            reasoning="The function should return a value",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        assert proposal.fix_id == "fix-001"
        assert proposal.error_id == "err-001"
        assert proposal.description == "Add return statement to foo()"
        assert len(proposal.code_changes) == 1
        assert proposal.confidence_score == 0.85
        assert proposal.reasoning == "The function should return a value"
        assert proposal.affected_files == ["src/module.py"]
        assert proposal.requires_manual_review is False

    def test_fix_proposal_default_status(self):
        """Verify FixProposal has PENDING as default status."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        proposal = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Test fix",
            code_changes=[change],
            confidence_score=0.5,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        assert proposal.status == FixStatus.PENDING

    def test_fix_proposal_timestamp_default(self):
        """Verify FixProposal has current timestamp as default."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        before = datetime.now()
        proposal = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Test fix",
            code_changes=[change],
            confidence_score=0.5,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )
        after = datetime.now()

        assert before <= proposal.timestamp <= after

    def test_fix_proposal_confidence_score_bounds(self):
        """Verify FixProposal accepts confidence scores in valid range."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        # Test minimum confidence
        proposal_min = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Test",
            code_changes=[change],
            confidence_score=0.0,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=True,
        )
        assert proposal_min.confidence_score == 0.0

        # Test maximum confidence
        proposal_max = FixProposal(
            fix_id="fix-002",
            error_id="err-001",
            description="Test",
            code_changes=[change],
            confidence_score=1.0,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )
        assert proposal_max.confidence_score == 1.0

    def test_fix_proposal_has_docstring(self):
        """Verify FixProposal has a docstring."""
        assert FixProposal.__doc__ is not None
        assert len(FixProposal.__doc__) > 0


class TestCheckpoint:
    """Test Checkpoint dataclass."""

    def test_checkpoint_creation(self):
        """Verify Checkpoint can be created with all fields."""
        now = datetime.now()
        retention = now + timedelta(hours=24)
        file_contents = {
            "src/module.py": "def foo():\n    pass",
            "src/other.py": "x = 1",
        }
        system_state = {"version": "1.0", "status": "running"}

        checkpoint = Checkpoint(
            checkpoint_id="cp-001",
            timestamp=now,
            affected_files=["src/module.py", "src/other.py"],
            file_contents=file_contents,
            system_state=system_state,
            retention_until=retention,
        )

        assert checkpoint.checkpoint_id == "cp-001"
        assert checkpoint.timestamp == now
        assert checkpoint.affected_files == ["src/module.py", "src/other.py"]
        assert checkpoint.file_contents == file_contents
        assert checkpoint.system_state == system_state
        assert checkpoint.retention_until == retention

    def test_checkpoint_retention_period(self):
        """Verify Checkpoint retention_until is 24 hours from creation."""
        now = datetime.now()
        retention = now + timedelta(hours=24)

        checkpoint = Checkpoint(
            checkpoint_id="cp-001",
            timestamp=now,
            affected_files=["src/module.py"],
            file_contents={"src/module.py": "content"},
            system_state={},
            retention_until=retention,
        )

        time_diff = checkpoint.retention_until - checkpoint.timestamp
        assert time_diff == timedelta(hours=24)

    def test_checkpoint_has_docstring(self):
        """Verify Checkpoint has a docstring."""
        assert Checkpoint.__doc__ is not None
        assert len(Checkpoint.__doc__) > 0


class TestLearningEntry:
    """Test LearningEntry dataclass."""

    def test_learning_entry_creation_with_all_fields(self):
        """Verify LearningEntry can be created with all fields."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        now = datetime.now()
        entry = LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError_invalid_input",
            error_type="ValueError",
            error_message_pattern="Invalid input",
            fix_description="Add input validation",
            code_changes=[change],
            reasoning="Input validation prevents errors",
            confidence_score=0.9,
            usage_count=5,
            success_count=4,
            failure_count=1,
            success_rate=0.8,
            created_at=now,
            last_used_at=now,
            archived=False,
        )

        assert entry.entry_id == "le-001"
        assert entry.error_pattern == "ValueError_invalid_input"
        assert entry.error_type == "ValueError"
        assert entry.error_message_pattern == "Invalid input"
        assert entry.fix_description == "Add input validation"
        assert len(entry.code_changes) == 1
        assert entry.reasoning == "Input validation prevents errors"
        assert entry.confidence_score == 0.9
        assert entry.usage_count == 5
        assert entry.success_count == 4
        assert entry.failure_count == 1
        assert entry.success_rate == 0.8
        assert entry.created_at == now
        assert entry.last_used_at == now
        assert entry.archived is False

    def test_learning_entry_default_values(self):
        """Verify LearningEntry has correct default values."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        entry = LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError",
            error_type="ValueError",
            error_message_pattern="Invalid",
            fix_description="Fix",
            code_changes=[change],
            reasoning="Reason",
            confidence_score=0.5,
        )

        assert entry.usage_count == 0
        assert entry.success_count == 0
        assert entry.failure_count == 0
        assert entry.success_rate == 0.0
        assert entry.last_used_at is None
        assert entry.archived is False

    def test_learning_entry_created_at_default(self):
        """Verify LearningEntry has current timestamp as default for created_at."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        before = datetime.now()
        entry = LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError",
            error_type="ValueError",
            error_message_pattern="Invalid",
            fix_description="Fix",
            code_changes=[change],
            reasoning="Reason",
            confidence_score=0.5,
        )
        after = datetime.now()

        assert before <= entry.created_at <= after

    def test_learning_entry_has_docstring(self):
        """Verify LearningEntry has a docstring."""
        assert LearningEntry.__doc__ is not None
        assert len(LearningEntry.__doc__) > 0


class TestDataModelDocstrings:
    """Test that all data models have comprehensive docstrings."""

    def test_all_enums_have_docstrings(self):
        """Verify all enum classes have docstrings."""
        assert ErrorSeverity.__doc__ is not None
        assert FixStatus.__doc__ is not None

    def test_all_dataclasses_have_docstrings(self):
        """Verify all dataclass classes have docstrings."""
        assert ErrorReport.__doc__ is not None
        assert CodeChange.__doc__ is not None
        assert FixProposal.__doc__ is not None
        assert Checkpoint.__doc__ is not None
        assert LearningEntry.__doc__ is not None

    def test_enum_members_have_docstrings(self):
        """Verify enum members have docstrings in class docstring."""
        assert "CRITICAL" in ErrorSeverity.__doc__
        assert "HIGH" in ErrorSeverity.__doc__
        assert "MEDIUM" in ErrorSeverity.__doc__
        assert "LOW" in ErrorSeverity.__doc__
        assert "INFO" in ErrorSeverity.__doc__

        assert "PENDING" in FixStatus.__doc__
        assert "APPLIED" in FixStatus.__doc__
        assert "VERIFIED" in FixStatus.__doc__
        assert "FAILED" in FixStatus.__doc__
        assert "REVERTED" in FixStatus.__doc__


class TestDataModelTypeHints:
    """Test that all data models have proper type hints."""

    def test_error_report_type_hints(self):
        """Verify ErrorReport has correct type hints."""
        annotations = ErrorReport.__annotations__
        assert annotations["error_id"] == str
        assert annotations["error_type"] == str
        assert annotations["message"] == str
        assert annotations["severity"] == ErrorSeverity
        assert annotations["timestamp"] == datetime
        assert annotations["component"] == str
        assert annotations["context"] == Dict[str, Any]
        assert annotations["stack_trace"] == str
        assert annotations["file_path"] == str
        assert annotations["line_number"] == int
        assert annotations["occurrence_count"] == int
        assert annotations["status"] == str

    def test_code_change_type_hints(self):
        """Verify CodeChange has correct type hints."""
        annotations = CodeChange.__annotations__
        assert annotations["file_path"] == str
        assert annotations["original_content"] == str
        assert annotations["new_content"] == str
        assert annotations["line_start"] == int
        assert annotations["line_end"] == int
        assert annotations["diff"] == str

    def test_fix_proposal_type_hints(self):
        """Verify FixProposal has correct type hints."""
        annotations = FixProposal.__annotations__
        assert annotations["fix_id"] == str
        assert annotations["error_id"] == str
        assert annotations["description"] == str
        assert annotations["code_changes"] == List[CodeChange]
        assert annotations["confidence_score"] == float
        assert annotations["reasoning"] == str
        assert annotations["affected_files"] == List[str]
        assert annotations["requires_manual_review"] == bool
        assert annotations["status"] == FixStatus
        assert annotations["timestamp"] == datetime

    def test_checkpoint_type_hints(self):
        """Verify Checkpoint has correct type hints."""
        annotations = Checkpoint.__annotations__
        assert annotations["checkpoint_id"] == str
        assert annotations["timestamp"] == datetime
        assert annotations["affected_files"] == List[str]
        assert annotations["file_contents"] == Dict[str, str]
        assert annotations["system_state"] == Dict[str, Any]
        assert annotations["retention_until"] == datetime

    def test_learning_entry_type_hints(self):
        """Verify LearningEntry has correct type hints."""
        annotations = LearningEntry.__annotations__
        assert annotations["entry_id"] == str
        assert annotations["error_pattern"] == str
        assert annotations["error_type"] == str
        assert annotations["error_message_pattern"] == str
        assert annotations["fix_description"] == str
        assert annotations["code_changes"] == List[CodeChange]
        assert annotations["reasoning"] == str
        assert annotations["confidence_score"] == float
        assert annotations["usage_count"] == int
        assert annotations["success_count"] == int
        assert annotations["failure_count"] == int
        assert annotations["success_rate"] == float
        assert annotations["created_at"] == datetime
        assert annotations["last_used_at"] == Optional[datetime]
        assert annotations["archived"] == bool


class TestDataModelIntegration:
    """Test integration between data models."""

    def test_error_report_to_fix_proposal_flow(self):
        """Verify ErrorReport can be used to create FixProposal."""
        error = ErrorReport(
            error_id="err-001",
            error_type="ValueError",
            message="Invalid value",
            severity=ErrorSeverity.HIGH,
            timestamp=datetime.now(),
            component="Root_Orchestrator",
            context={"trace_id": "trace-123"},
            stack_trace="",
            file_path="src/module.py",
            line_number=42,
        )

        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=42,
            line_end=42,
            diff="",
        )

        proposal = FixProposal(
            fix_id="fix-001",
            error_id=error.error_id,
            description="Fix for " + error.message,
            code_changes=[change],
            confidence_score=0.8,
            reasoning="Based on error analysis",
            affected_files=[error.file_path],
            requires_manual_review=False,
        )

        assert proposal.error_id == error.error_id
        assert error.file_path in proposal.affected_files

    def test_fix_proposal_to_checkpoint_flow(self):
        """Verify FixProposal can be used with Checkpoint."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="def foo():\n    pass",
            new_content="def foo():\n    return 42",
            line_start=1,
            line_end=2,
            diff="",
        )

        proposal = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Add return",
            code_changes=[change],
            confidence_score=0.9,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        now = datetime.now()
        checkpoint = Checkpoint(
            checkpoint_id="cp-001",
            timestamp=now,
            affected_files=proposal.affected_files,
            file_contents={"src/module.py": change.original_content},
            system_state={},
            retention_until=now + timedelta(hours=24),
        )

        assert checkpoint.affected_files == proposal.affected_files
        assert "src/module.py" in checkpoint.file_contents

    def test_fix_proposal_to_learning_entry_flow(self):
        """Verify FixProposal can be converted to LearningEntry."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        proposal = FixProposal(
            fix_id="fix-001",
            error_id="err-001",
            description="Add validation",
            code_changes=[change],
            confidence_score=0.85,
            reasoning="Input validation prevents errors",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        entry = LearningEntry(
            entry_id="le-001",
            error_pattern="ValueError_invalid",
            error_type="ValueError",
            error_message_pattern="Invalid input",
            fix_description=proposal.description,
            code_changes=proposal.code_changes,
            reasoning=proposal.reasoning,
            confidence_score=proposal.confidence_score,
        )

        assert entry.fix_description == proposal.description
        assert entry.confidence_score == proposal.confidence_score
        assert len(entry.code_changes) == len(proposal.code_changes)
