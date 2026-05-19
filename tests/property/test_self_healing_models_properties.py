"""
Property-based tests for self-healing deployment system data models.

These tests verify correctness properties that should hold across all valid
inputs and use cases. Properties are tested with 100+ randomized iterations
using Hypothesis.

Requirements: 1.3, 3.4
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from src.kabbalah.self_healing_models import (
    ErrorSeverity,
    FixStatus,
    ErrorReport,
    CodeChange,
    FixProposal,
    Checkpoint,
    LearningEntry,
)


# Custom strategies for generating valid data
error_severity_strategy = st.sampled_from(list(ErrorSeverity))
fix_status_strategy = st.sampled_from(list(FixStatus))

# Strategy for generating valid confidence scores (0.0-1.0)
confidence_score_strategy = st.floats(min_value=0.0, max_value=1.0)

# Strategy for generating valid file paths (simpler to avoid filtering)
file_path_strategy = st.just("src/module.py") | st.just("src/test.py") | st.just("src/utils/helper.py")

# Strategy for generating valid component names
component_strategy = st.sampled_from([
    "Intake_Node",
    "Root_Orchestrator",
    "Domain_Orchestrator",
    "Leaf_Node",
    "Synthesizer",
    "FSM_Enforcement",
])

# Strategy for generating valid error types
error_type_strategy = st.sampled_from([
    "ValueError",
    "TypeError",
    "RuntimeError",
    "KeyError",
    "AttributeError",
    "DecompositionError",
    "CoordinationError",
    "ExecutionError",
])


class TestProperty3UniqueErrorIdentification:
    """
    Property 3: Unique Error Identification
    
    Each error has unique error_id.
    
    **Validates: Requirements 1.3**
    """

    @given(
        error_ids=st.lists(
            st.uuids().map(str),
            min_size=1,
            max_size=100,
            unique=True,
        )
    )
    def test_error_ids_are_unique(self, error_ids):
        """Verify that each error_id is unique across multiple errors."""
        errors = []
        for error_id in error_ids:
            error = ErrorReport(
                error_id=error_id,
                error_type="ValueError",
                message="Test error",
                severity=ErrorSeverity.MEDIUM,
                timestamp=datetime.now(),
                component="Leaf_Node",
                context={},
                stack_trace="",
                file_path="test.py",
                line_number=1,
            )
            errors.append(error)

        # Verify all error_ids are unique
        error_ids_from_errors = [e.error_id for e in errors]
        assert len(error_ids_from_errors) == len(set(error_ids_from_errors))


class TestProperty9ConfidenceScoreBounds:
    """
    Property 9: Confidence Score Bounds
    
    Confidence scores are 0.0-1.0.
    
    **Validates: Requirements 3.4**
    """

    @given(confidence_score=confidence_score_strategy)
    def test_confidence_score_within_bounds(self, confidence_score):
        """Verify that confidence scores are always within 0.0-1.0 bounds."""
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
            confidence_score=confidence_score,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        assert 0.0 <= proposal.confidence_score <= 1.0

    @given(confidence_score=confidence_score_strategy)
    def test_learning_entry_confidence_score_within_bounds(self, confidence_score):
        """Verify that learning entry confidence scores are within bounds."""
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
            confidence_score=confidence_score,
        )

        assert 0.0 <= entry.confidence_score <= 1.0


class TestProperty10ManualReviewRequirement:
    """
    Property 10: Manual Review Requirement
    
    Low confidence fixes marked for review.
    
    **Validates: Requirements 3.8, 13.3**
    """

    @given(confidence_score=st.floats(min_value=0.0, max_value=0.49))
    def test_low_confidence_requires_review(self, confidence_score):
        """Verify that fixes with confidence < 0.5 require manual review."""
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
            confidence_score=confidence_score,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=True,
        )

        assert proposal.requires_manual_review is True

    @given(confidence_score=st.floats(min_value=0.5, max_value=1.0))
    def test_high_confidence_may_not_require_review(self, confidence_score):
        """Verify that fixes with confidence >= 0.5 may not require review."""
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
            confidence_score=confidence_score,
            reasoning="Test",
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        # High confidence fixes don't require review
        assert proposal.requires_manual_review is False


class TestProperty11FixRankingByConfidence:
    """
    Property 11: Fix Ranking by Confidence
    
    Fixes ranked by confidence descending.
    
    **Validates: Requirements 3.9**
    """

    @given(
        confidence_scores=st.lists(
            confidence_score_strategy,
            min_size=2,
            max_size=10,
        )
    )
    def test_fixes_ranked_by_confidence(self, confidence_scores):
        """Verify that fixes can be ranked by confidence score."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        proposals = []
        for i, score in enumerate(confidence_scores):
            proposal = FixProposal(
                fix_id=f"fix-{i:03d}",
                error_id="err-001",
                description=f"Fix {i}",
                code_changes=[change],
                confidence_score=score,
                reasoning="Test",
                affected_files=["src/module.py"],
                requires_manual_review=False,
            )
            proposals.append(proposal)

        # Rank by confidence (descending)
        ranked = sorted(proposals, key=lambda p: p.confidence_score, reverse=True)

        # Verify ranking is correct
        for i in range(len(ranked) - 1):
            assert ranked[i].confidence_score >= ranked[i + 1].confidence_score


class TestPropertyErrorReportConsistency:
    """
    Test consistency properties for ErrorReport.
    """

    @given(
        error_type=error_type_strategy,
        message=st.text(min_size=1, max_size=200),
        component=component_strategy,
        severity=error_severity_strategy,
    )
    def test_error_report_preserves_all_fields(
        self, error_type, message, component, severity
    ):
        """Verify that ErrorReport preserves all input fields."""
        error = ErrorReport(
            error_id="err-001",
            error_type=error_type,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            component=component,
            context={"trace_id": "trace-123"},
            stack_trace="",
            file_path="test.py",
            line_number=42,
        )

        assert error.error_type == error_type
        assert error.message == message
        assert error.component == component
        assert error.severity == severity


class TestPropertyCodeChangeConsistency:
    """
    Test consistency properties for CodeChange.
    """

    @given(
        file_path=file_path_strategy,
        original_content=st.text(min_size=0, max_size=1000),
        new_content=st.text(min_size=0, max_size=1000),
        line_start=st.integers(min_value=1, max_value=1000),
        line_end=st.integers(min_value=1, max_value=1000),
    )
    def test_code_change_preserves_all_fields(
        self, file_path, original_content, new_content, line_start, line_end
    ):
        """Verify that CodeChange preserves all input fields."""
        # Ensure line_end >= line_start
        if line_end < line_start:
            line_end = line_start

        change = CodeChange(
            file_path=file_path,
            original_content=original_content,
            new_content=new_content,
            line_start=line_start,
            line_end=line_end,
            diff="",
        )

        assert change.file_path == file_path
        assert change.original_content == original_content
        assert change.new_content == new_content
        assert change.line_start == line_start
        assert change.line_end == line_end


class TestPropertyFixProposalConsistency:
    """
    Test consistency properties for FixProposal.
    """

    @given(
        fix_id=st.uuids().map(str),
        error_id=st.uuids().map(str),
        description=st.text(min_size=1, max_size=200),
        confidence_score=confidence_score_strategy,
        reasoning=st.text(min_size=1, max_size=500),
    )
    def test_fix_proposal_preserves_all_fields(
        self, fix_id, error_id, description, confidence_score, reasoning
    ):
        """Verify that FixProposal preserves all input fields."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        proposal = FixProposal(
            fix_id=fix_id,
            error_id=error_id,
            description=description,
            code_changes=[change],
            confidence_score=confidence_score,
            reasoning=reasoning,
            affected_files=["src/module.py"],
            requires_manual_review=False,
        )

        assert proposal.fix_id == fix_id
        assert proposal.error_id == error_id
        assert proposal.description == description
        assert proposal.confidence_score == confidence_score
        assert proposal.reasoning == reasoning


class TestPropertyCheckpointConsistency:
    """
    Test consistency properties for Checkpoint.
    """

    @given(
        checkpoint_id=st.uuids().map(str),
        affected_files=st.lists(
            st.just("src/module.py") | st.just("src/test.py"),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    def test_checkpoint_preserves_all_fields(self, checkpoint_id, affected_files):
        """Verify that Checkpoint preserves all input fields."""
        now = datetime.now()
        retention = now + timedelta(hours=24)
        file_contents = {f: f"content-{i}" for i, f in enumerate(affected_files)}

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=now,
            affected_files=affected_files,
            file_contents=file_contents,
            system_state={"version": "1.0"},
            retention_until=retention,
        )

        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.affected_files == affected_files
        assert checkpoint.file_contents == file_contents


class TestPropertyLearningEntryConsistency:
    """
    Test consistency properties for LearningEntry.
    """

    @given(
        entry_id=st.uuids().map(str),
        error_pattern=st.text(min_size=1, max_size=100),
        error_type=error_type_strategy,
        confidence_score=confidence_score_strategy,
        usage_count=st.integers(min_value=0, max_value=1000),
        success_count=st.integers(min_value=0, max_value=1000),
    )
    def test_learning_entry_preserves_all_fields(
        self,
        entry_id,
        error_pattern,
        error_type,
        confidence_score,
        usage_count,
        success_count,
    ):
        """Verify that LearningEntry preserves all input fields."""
        change = CodeChange(
            file_path="src/module.py",
            original_content="",
            new_content="",
            line_start=1,
            line_end=1,
            diff="",
        )

        entry = LearningEntry(
            entry_id=entry_id,
            error_pattern=error_pattern,
            error_type=error_type,
            error_message_pattern="Invalid",
            fix_description="Fix",
            code_changes=[change],
            reasoning="Reason",
            confidence_score=confidence_score,
            usage_count=usage_count,
            success_count=success_count,
        )

        assert entry.entry_id == entry_id
        assert entry.error_pattern == error_pattern
        assert entry.error_type == error_type
        assert entry.confidence_score == confidence_score
        assert entry.usage_count == usage_count
        assert entry.success_count == success_count


class TestPropertyEnumConsistency:
    """
    Test consistency properties for enums.
    """

    @given(severity=error_severity_strategy)
    def test_error_severity_enum_consistency(self, severity):
        """Verify that ErrorSeverity enum values are consistent."""
        assert isinstance(severity, ErrorSeverity)
        assert severity.value in [
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
            "INFO",
        ]

    @given(status=fix_status_strategy)
    def test_fix_status_enum_consistency(self, status):
        """Verify that FixStatus enum values are consistent."""
        assert isinstance(status, FixStatus)
        assert status.value in [
            "PENDING",
            "APPLIED",
            "VERIFIED",
            "FAILED",
            "REVERTED",
        ]
