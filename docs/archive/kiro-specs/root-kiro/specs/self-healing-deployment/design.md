# Self-Healing Deployment System - Technical Design Document

## Overview

The Self-Healing Deployment System is an autonomous error detection, analysis, and correction framework integrated with the Kabbalah multi-agent orchestration platform. The system operates as a closed-loop feedback mechanism that continuously monitors for errors, analyzes root causes using a local LLM, generates and applies fixes safely, verifies corrections through automated testing, and learns from successful patterns to improve future error resolution.

### Key Design Principles

1. **Local-First Architecture**: All error analysis uses a local LLM (Ollama/Llama) to eliminate external API dependencies, reduce latency, and maintain privacy
2. **Safety-First Approach**: Atomic operations, checkpoint-based rollback, and confidence-based manual review prevent cascading failures
3. **Learning-Driven Evolution**: Persistent learning database enables pattern recognition and accelerates fix application for recurring errors
4. **Minimal Performance Impact**: Error detection (<10ms), fix application (<2s), and background learning ensure system responsiveness
5. **Comprehensive Observability**: Full audit trails, metrics collection, and monitoring enable operational visibility and compliance

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Kabbalah Components                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Intake_Node  │  │Root_Orch.    │  │Domain_Orch.  │  │ Leaf_Nodes   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         └─────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                    ┌──────▼─────────────────▼──────┐                       │
│                    │  Error Detection Hooks        │                       │
│                    │  (Exception Handlers)         │                       │
│                    └──────┬──────────────────────┬──┘                       │
└─────────────────────────────┼──────────────────────┼──────────────────────┘
                              │                      │
                    ┌─────────▼──────────────────────▼────────┐
                    │   Error Detection Module                │
                    │  - Capture exceptions/test failures     │
                    │  - Assign error_id, severity            │
                    │  - Deduplication (60s window)           │
                    │  - Store ErrorReport                    │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Error Analysis Module                │
                    │  - Generate analysis prompt            │
                    │  - Invoke Local_LLM (300s timeout)     │
                    │  - Parse response                      │
                    │  - Fallback to Learning_Database       │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Fix Generation Module                │
                    │  - Extract code changes                │
                    │  - Calculate confidence_score          │
                    │  - Validate syntax                     │
                    │  - Rank by confidence                  │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Safety Module                        │
                    │  - Validate fix safety                 │
                    │  - Check confidence threshold          │
                    │  - Enforce manual review               │
                    │  - Prevent concurrent fixes            │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Fix Application Module               │
                    │  - Create checkpoint                   │
                    │  - Apply changes atomically            │
                    │  - Log all modifications               │
                    │  - Rollback on failure                 │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Fix Verification Module              │
                    │  - Run relevant test suite             │
                    │  - Compare system state                │
                    │  - Detect regressions                  │
                    │  - Timeout after 600s                  │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Learning System                      │
                    │  - Store verified fixes                │
                    │  - Index patterns                      │
                    │  - Track usage/success rate            │
                    │  - Archive old entries (>30 days)      │
                    └─────────┬──────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────┐
                    │   Monitoring & Audit System            │
                    │  - Collect metrics                     │
                    │  - Expose Prometheus endpoint          │
                    │  - Maintain immutable audit log        │
                    │  - Alert on critical events            │
                    └────────────────────────────────────────┘
```

### Component Integration Points

The system integrates with Kabbalah components through standardized error hooks:

1. **Intake_Node**: Captures parsing errors, specification validation failures
2. **Root_Orchestrator**: Captures decomposition errors, orchestration failures
3. **Domain_Orchestrator**: Captures coordination errors, domain-specific failures
4. **Leaf_Nodes**: Captures task execution errors, resource failures
5. **Synthesizer**: Captures result consolidation errors, synthesis failures
6. **FSM_Enforcement**: Captures state machine violations as CRITICAL errors
7. **Test Framework**: Captures pytest failures with full context

---

## Components and Interfaces

### 1. Error Detection Module

**Responsibility**: Capture, classify, and deduplicate errors from all system components

**Key Interfaces**:

```python
class ErrorDetectionModule:
    def capture_exception(
        self,
        exception: Exception,
        component: str,
        context: Dict[str, Any]
    ) -> ErrorReport:
        """
        Capture a runtime exception with full context.

        Args:
            exception: The caught exception
            component: Name of component where error occurred
            context: Execution context (trace_id, request_id, etc.)

        Returns:
            ErrorReport with unique error_id and severity classification
        """

    def capture_test_failure(
        self,
        test_name: str,
        failure_message: str,
        assertion_details: Dict[str, Any],
        test_context: Dict[str, Any]
    ) -> ErrorReport:
        """
        Capture a test failure with assertion details.
        """

    def deduplicate_error(
        self,
        error_report: ErrorReport,
        window_seconds: int = 60
    ) -> Optional[ErrorReport]:
        """
        Check if identical error occurred recently.
        Returns None if duplicate (increments counter), else returns report.
        """

    def classify_severity(
        self,
        component: str,
        error_type: str,
        affected_components: List[str]
    ) -> ErrorSeverity:
        """
        Classify error severity based on component and scope.
        CRITICAL: Intake_Node, Root_Orchestrator, Synthesizer
        HIGH: Domain_Orchestrator, test failures, multi-component impact
        MEDIUM: Leaf_Node, single component
        LOW: Warnings, non-blocking errors
        """
```

**Data Structures**:

```python
@dataclass
class ErrorReport:
    error_id: str  # UUID
    error_type: str  # Exception class name
    message: str
    severity: ErrorSeverity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    timestamp: datetime
    component: str
    context: Dict[str, Any]  # trace_id, request_id, etc.
    stack_trace: str
    file_path: str
    line_number: int
    occurrence_count: int = 1  # Incremented for duplicates
    status: str = "DETECTED"  # DETECTED, ANALYZED, FIXED, VERIFIED, FAILED
```

### 2. Error Analysis Module

**Responsibility**: Analyze errors using local LLM and fallback to learning database

**Key Interfaces**:

```python
class ErrorAnalysisModule:
    def analyze_error(
        self,
        error_report: ErrorReport,
        learning_context: Optional[List[LearningEntry]] = None
    ) -> ErrorAnalysis:
        """
        Analyze error using Local_LLM with learning database context.

        Timeout: 300 seconds
        Fallback: If LLM unavailable, use learning database only
        """

    def generate_analysis_prompt(
        self,
        error_report: ErrorReport,
        similar_fixes: List[LearningEntry]
    ) -> str:
        """
        Generate structured prompt for LLM analysis.
        Includes error details, stack trace, similar patterns from learning DB.
        """

    def parse_llm_response(
        self,
        response: str
    ) -> Tuple[str, List[str], float]:
        """
        Parse LLM response to extract:
        - Root cause analysis (str)
        - Affected files (List[str])
        - Confidence score (float 0.0-1.0)
        """

@dataclass
class ErrorAnalysis:
    error_id: str
    root_cause: str
    suggested_fixes: List[str]
    affected_files: List[str]
    confidence_score: float
    reasoning: str
    llm_model: str
    analysis_time_ms: float
    timestamp: datetime
    used_learning_database: bool
```

### 3. Fix Generation Module

**Responsibility**: Generate code fixes from error analysis with validation

**Key Interfaces**:

```python
class FixGenerationModule:
    def generate_fix(
        self,
        error_analysis: ErrorAnalysis
    ) -> FixProposal:
        """
        Generate fix proposal from error analysis.

        Validates:
        - Syntax correctness of proposed changes
        - File paths are valid
        - Changes are non-empty
        """

    def extract_code_changes(
        self,
        analysis_text: str
    ) -> List[CodeChange]:
        """
        Extract file paths and new content from LLM analysis.
        """

    def validate_syntax(
        self,
        file_path: str,
        new_content: str
    ) -> bool:
        """
        Validate that proposed content is syntactically correct.
        """

    def rank_fixes(
        self,
        fixes: List[FixProposal]
    ) -> List[FixProposal]:
        """
        Rank fixes by confidence_score (highest first).
        """

@dataclass
class CodeChange:
    file_path: str
    original_content: str
    new_content: str
    line_start: int
    line_end: int
    diff: str

@dataclass
class FixProposal:
    fix_id: str  # UUID
    error_id: str
    description: str
    code_changes: List[CodeChange]
    confidence_score: float  # 0.0-1.0
    reasoning: str
    affected_files: List[str]
    requires_manual_review: bool  # True if confidence < 0.5
    status: str = "PENDING"  # PENDING, APPLIED, VERIFIED, FAILED, REVERTED
    timestamp: datetime = field(default_factory=datetime.now)
```

### 4. Fix Application Module

**Responsibility**: Safely apply fixes with atomic operations and rollback capability

**Key Interfaces**:

```python
class FixApplicationModule:
    def apply_fix(
        self,
        fix_proposal: FixProposal
    ) -> FixApplicationResult:
        """
        Apply fix atomically with checkpoint creation.

        Process:
        1. Create checkpoint of all affected files
        2. Apply all changes atomically
        3. Verify system consistency
        4. Update fix status to APPLIED

        On failure: Rollback and update status to REVERTED
        """

    def create_checkpoint(
        self,
        affected_files: List[str]
    ) -> Checkpoint:
        """
        Create backup checkpoint before applying fix.
        Checkpoint retained for 24 hours.
        """

    def apply_changes_atomically(
        self,
        code_changes: List[CodeChange]
    ) -> bool:
        """
        Apply all changes or none (atomic operation).
        Prevents concurrent modifications to same files.
        """

    def verify_consistency(self) -> bool:
        """
        Verify system remains in consistent state after changes.
        """

    def rollback_to_checkpoint(
        self,
        checkpoint: Checkpoint
    ) -> bool:
        """
        Restore all files to checkpoint state.
        """

@dataclass
class Checkpoint:
    checkpoint_id: str  # UUID
    timestamp: datetime
    affected_files: List[str]
    file_contents: Dict[str, str]  # file_path -> content
    system_state: Dict[str, Any]
    retention_until: datetime  # 24 hours from creation

@dataclass
class FixApplicationResult:
    fix_id: str
    success: bool
    checkpoint_id: Optional[str]
    changes_applied: int
    error_message: Optional[str]
    timestamp: datetime
```

### 5. Fix Verification Module

**Responsibility**: Verify fixes through automated testing and regression detection

**Key Interfaces**:

```python
class FixVerificationModule:
    def verify_fix(
        self,
        fix_proposal: FixProposal
    ) -> VerificationResult:
        """
        Run verification tests for applied fix.

        Timeout: 600 seconds
        On failure: Trigger rollback and new error analysis
        """

    def identify_relevant_tests(
        self,
        affected_files: List[str],
        error_component: str
    ) -> List[str]:
        """
        Identify test suite relevant to error and affected files.
        """

    def run_tests(
        self,
        test_paths: List[str],
        timeout_seconds: int = 600
    ) -> TestExecutionResult:
        """
        Execute tests with timeout.
        """

    def detect_regressions(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> List[str]:
        """
        Compare system state before/after to detect regressions.
        """

@dataclass
class VerificationResult:
    fix_id: str
    success: bool
    tests_passed: int
    tests_failed: int
    test_execution_time_ms: float
    regressions_detected: List[str]
    new_errors: List[ErrorReport]
    timestamp: datetime
```

### 6. Learning System

**Responsibility**: Store, index, and reuse successful fixes

**Key Interfaces**:

```python
class LearningSystem:
    def learn_fix(
        self,
        error_report: ErrorReport,
        fix_proposal: FixProposal,
        verification_result: VerificationResult
    ) -> LearningEntry:
        """
        Store verified fix in learning database.
        """

    def find_similar_errors(
        self,
        error_report: ErrorReport,
        top_k: int = 5
    ) -> List[LearningEntry]:
        """
        Find similar patterns in learning database.
        Uses error type, message similarity, and pattern matching.
        """

    def calculate_similarity_score(
        self,
        error1: ErrorReport,
        error2: ErrorReport
    ) -> float:
        """
        Calculate similarity between two errors (0.0-1.0).
        Considers: error_type, message similarity, component, context.
        """

    def update_confidence_score(
        self,
        learning_entry_id: str,
        success: bool
    ) -> None:
        """
        Update confidence based on success/failure.
        Increment usage counter.
        """

    def archive_old_entries(
        self,
        older_than_days: int = 30
    ) -> int:
        """
        Archive entries older than threshold.
        Returns count of archived entries.
        """

    def persist_database(self) -> None:
        """
        Persist learning database to disk.
        """

    def load_database(self) -> None:
        """
        Load learning database from disk on startup.
        """

@dataclass
class LearningEntry:
    entry_id: str  # UUID
    error_pattern: str  # Normalized error type/message
    error_type: str
    error_message_pattern: str
    fix_description: str
    code_changes: List[CodeChange]
    reasoning: str
    confidence_score: float  # Updated based on success/failure
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    archived: bool = False
```

### 7. Local LLM Manager

**Responsibility**: Manage Ollama/Llama integration with configuration and fallback

**Key Interfaces**:

```python
class LocalLLMManager:
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM manager with configuration.
        """

    def check_availability(self) -> bool:
        """
        Check if Ollama is running at configured base_url.
        """

    def load_model(self, model_name: str) -> bool:
        """
        Load specified model or pull from registry if not available.
        """

    def analyze_error(
        self,
        prompt: str,
        timeout_seconds: int = 300
    ) -> str:
        """
        Invoke LLM with error analysis prompt.
        Returns response or raises timeout exception.
        """

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get loaded model name, size, parameters.
        """

@dataclass
class LLMConfig:
    base_url: str = "http://localhost:11434"
    model_name: str = "llama2"
    temperature: float = 0.3  # Lower for more deterministic analysis
    top_p: float = 0.9
    top_k: int = 40
    timeout_seconds: int = 300
    max_tokens: int = 2048
```

### 8. Safety Module

**Responsibility**: Enforce safety constraints and prevent breaking changes

**Key Interfaces**:

```python
class SafetyModule:
    def validate_fix_safety(
        self,
        fix_proposal: FixProposal
    ) -> SafetyValidationResult:
        """
        Validate fix against safety constraints.
        """

    def check_critical_files(
        self,
        affected_files: List[str]
    ) -> List[str]:
        """
        Identify if fix modifies critical system files.
        Critical files: config, security, core orchestration.
        """

    def check_dependencies(
        self,
        code_changes: List[CodeChange]
    ) -> List[str]:
        """
        Detect if fix introduces new dependencies.
        """

    def check_api_compatibility(
        self,
        code_changes: List[CodeChange]
    ) -> bool:
        """
        Verify fix maintains backward compatibility.
        """

    def require_manual_review(
        self,
        fix_proposal: FixProposal
    ) -> bool:
        """
        Determine if fix requires manual review based on:
        - confidence_score < 0.5
        - Affects > 5 files
        - Modifies critical files
        - Introduces dependencies
        """

    def prevent_concurrent_fixes(self) -> bool:
        """
        Ensure only one fix applied at a time.
        """

@dataclass
class SafetyValidationResult:
    fix_id: str
    is_safe: bool
    requires_manual_review: bool
    violations: List[str]  # List of safety violations
    critical_files_affected: List[str]
    new_dependencies: List[str]
    api_compatibility_issues: List[str]
```

### 9. Monitoring System

**Responsibility**: Collect metrics, maintain audit logs, and expose observability

**Key Interfaces**:

```python
class MonitoringSystem:
    def record_error_detected(self, error_report: ErrorReport) -> None:
        """Record error detection event."""

    def record_error_analyzed(
        self,
        error_id: str,
        analysis_time_ms: float,
        confidence_score: float
    ) -> None:
        """Record error analysis event."""

    def record_fix_generated(
        self,
        fix_proposal: FixProposal
    ) -> None:
        """Record fix generation event."""

    def record_fix_applied(
        self,
        fix_id: str,
        success: bool,
        files_changed: int
    ) -> None:
        """Record fix application event."""

    def record_fix_verified(
        self,
        fix_id: str,
        success: bool,
        test_time_ms: float
    ) -> None:
        """Record fix verification event."""

    def record_fix_learned(
        self,
        learning_entry_id: str,
        pattern: str
    ) -> None:
        """Record learning event."""

    def get_metrics(self) -> MonitoringMetrics:
        """
        Get current metrics snapshot.
        """

    def expose_prometheus_metrics(self) -> str:
        """
        Expose metrics in Prometheus format.
        """

    def send_alert(
        self,
        severity: str,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Send alert notification (email, Slack, webhook).
        """

@dataclass
class MonitoringMetrics:
    total_errors_detected: int
    total_fixes_generated: int
    total_fixes_applied: int
    total_fixes_verified: int
    total_fixes_failed: int
    average_fix_time_ms: float
    average_analysis_time_ms: float
    learning_database_size: int
    verified_fixes_count: int
    failed_fixes_count: int
    timestamp: datetime
```

---

## Data Models

### Core Data Structures

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

class ErrorSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class FixStatus(Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REVERTED = "REVERTED"

@dataclass
class ErrorReport:
    """Structured record of detected error."""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    component: str
    context: Dict[str, Any]
    stack_trace: str
    file_path: str
    line_number: int
    occurrence_count: int = 1
    status: str = "DETECTED"

@dataclass
class FixProposal:
    """Proposed fix with code changes and confidence."""
    fix_id: str
    error_id: str
    description: str
    code_changes: List['CodeChange']
    confidence_score: float
    reasoning: str
    affected_files: List[str]
    requires_manual_review: bool
    status: FixStatus = FixStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CodeChange:
    """Individual file change within a fix."""
    file_path: str
    original_content: str
    new_content: str
    line_start: int
    line_end: int
    diff: str

@dataclass
class LearningEntry:
    """Stored pattern for fix reuse."""
    entry_id: str
    error_pattern: str
    error_type: str
    error_message_pattern: str
    fix_description: str
    code_changes: List[CodeChange]
    reasoning: str
    confidence_score: float
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    archived: bool = False

@dataclass
class Checkpoint:
    """Backup state for rollback."""
    checkpoint_id: str
    timestamp: datetime
    affected_files: List[str]
    file_contents: Dict[str, str]
    system_state: Dict[str, Any]
    retention_until: datetime
```

---

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

Before writing correctness properties, I need to analyze the acceptance criteria for testability using the prework tool.

### Property 1: Error Deduplication Within Time Window

_For any_ two identical errors detected within a 60-second window, the system SHALL create only one ErrorReport and increment the occurrence_count rather than creating duplicate reports.

**Validates: Requirements 1.6**

### Property 2: Severity Classification by Component

_For any_ error detected in a critical component (Intake_Node, Root_Orchestrator, Synthesizer), the system SHALL classify it as CRITICAL severity. For errors in non-critical components (Leaf_Node, Domain_Orchestrator), the system SHALL classify as HIGH or MEDIUM.

**Validates: Requirements 1.7, 1.8, 11.2, 11.3, 11.4**

### Property 3: Unique Error Identification

_For any_ set of detected errors, each error SHALL have a unique error_id and timestamp, with no two errors sharing the same error_id.

**Validates: Requirements 1.3**

### Property 4: Error Report Persistence

_For any_ detected error, querying the error_history after detection SHALL return the ErrorReport with all captured details (exception type, message, stack trace, context).

**Validates: Requirements 1.5**

### Property 5: LLM Response Parsing

_For any_ valid LLM response containing root cause analysis, suggested fixes, affected files, and confidence score, the Error_Analysis_Module SHALL correctly parse and extract all fields.

**Validates: Requirements 2.3**

### Property 6: Analysis Fallback to Learning Database

_For any_ error when the Local_LLM is unavailable, the Error_Analysis_Module SHALL fallback to searching the Learning_Database for similar patterns and return a valid analysis.

**Validates: Requirements 2.4**

### Property 7: Malformed LLM Response Handling

_For any_ malformed LLM response, the Error_Analysis_Module SHALL return a default analysis with low confidence (< 0.3) rather than crashing.

**Validates: Requirements 2.5**

### Property 8: Unique Fix Proposal Generation

_For any_ set of generated fix proposals, each fix SHALL have a unique fix_id with no duplicates.

**Validates: Requirements 3.1**

### Property 9: Confidence Score Bounds

_For any_ generated fix proposal, the confidence_score SHALL be between 0.0 and 1.0 (inclusive).

**Validates: Requirements 3.4**

### Property 10: Manual Review Requirement

_For any_ fix proposal with confidence_score < 0.5, the requires_manual_review flag SHALL be True.

**Validates: Requirements 3.8, 13.3**

### Property 11: Fix Ranking by Confidence

_For any_ set of multiple fix proposals for the same error, when ranked, the fixes SHALL be ordered by confidence_score in descending order.

**Validates: Requirements 3.9**

### Property 12: Atomic Fix Application

_For any_ fix with multiple file changes, either all changes SHALL be applied successfully and status updated to APPLIED, or all changes SHALL be rolled back and status updated to REVERTED.

**Validates: Requirements 4.2, 4.5**

### Property 13: Checkpoint Creation Before Application

_For any_ fix application, a checkpoint SHALL be created before any file changes are made, containing all affected file contents and system state.

**Validates: Requirements 4.1, 4.7**

### Property 14: Concurrent Modification Prevention

_For any_ two concurrent fix applications targeting the same file, the system SHALL prevent both from executing simultaneously and queue one for later execution.

**Validates: Requirements 4.8**

### Property 15: Test Selection for Verification

_For any_ fix affecting specific files and components, the Fix_Verification_Module SHALL select tests related to those files and components for execution.

**Validates: Requirements 5.2**

### Property 16: Verification Status Updates

_For any_ fix verification, if all tests pass, status SHALL be updated to VERIFIED. If any test fails, status SHALL be updated to FAILED and rollback SHALL be triggered.

**Validates: Requirements 5.3, 5.4**

### Property 17: Verification Timeout Enforcement

_For any_ fix verification that exceeds 600 seconds, the system SHALL timeout and mark the fix as FAILED.

**Validates: Requirements 5.7**

### Property 18: Learning Database Storage

_For any_ successfully verified fix, the Learning_System SHALL store the fix pattern in the Learning_Database with all required fields (error_pattern, fix_description, code_changes, reasoning, confidence_score).

**Validates: Requirements 6.1, 6.2**

### Property 19: Similar Pattern Discovery

_For any_ new error, the Learning_System SHALL search the Learning_Database and return similar patterns ranked by relevance and confidence score.

**Validates: Requirements 6.4, 6.5**

### Property 20: Learning Entry Usage Tracking

_For any_ learned fix that is applied, the usage_count SHALL be incremented and success_rate SHALL be updated based on verification outcome.

**Validates: Requirements 6.6, 6.7**

### Property 21: Learning Database Archival

_For any_ Learning_Database with 1000+ entries, entries older than 30 days SHALL be archived and remain searchable.

**Validates: Requirements 6.8, 12.4**

### Property 22: LLM Parameter Configuration

_For any_ LLM configuration with temperature, top_p, and top_k parameters, the Local_LLM_Manager SHALL accept and apply these parameters to LLM invocations.

**Validates: Requirements 7.6**

### Property 23: LLM Timeout Enforcement

_For any_ LLM invocation that exceeds 300 seconds, the Local_LLM_Manager SHALL timeout and return an error.

**Validates: Requirements 7.7**

### Property 24: Graceful LLM Degradation

_For any_ system deployment without Ollama available, the system SHALL operate in Learning_Database-only mode without crashing.

**Validates: Requirements 7.9**

### Property 25: Safety Validation for Critical Files

_For any_ fix proposal that modifies critical system files (configuration, security, core orchestration), the Safety_Module SHALL flag it as requiring manual review.

**Validates: Requirements 10.1, 10.4**

### Property 26: Concurrent Fix Prevention

_For any_ two fix applications, the system SHALL prevent both from executing concurrently and ensure only one fix is applied at a time.

**Validates: Requirements 10.6**

### Property 27: Rollback Checkpoint Retention

_For any_ applied fix, the checkpoint SHALL be retained for 24 hours and allow rollback within that period.

**Validates: Requirements 14.1, 14.8**

### Property 28: Automatic Rollback on Verification Failure

_For any_ fix that fails verification, the system SHALL automatically rollback to the most recent checkpoint and restore the pre-fix state.

**Validates: Requirements 14.2, 14.3**

### Property 29: Error Detection Latency

_For any_ runtime exception, the Error_Detection_System SHALL capture and record it within 10 milliseconds.

**Validates: Requirements 16.1**

### Property 30: Fix Application Latency

_For any_ fix application, the system SHALL complete all file changes within 2 seconds.

**Validates: Requirements 16.4**

### Property 31: Learning Database Query Performance

_For any_ Learning_Database query with 1000+ entries, the system SHALL return results within 100 milliseconds.

**Validates: Requirements 6.9, 12.9, 16.8**

---

## Error Handling

### Error Detection and Classification

The system implements comprehensive error handling across all layers:

1. **Exception Capture**: All exceptions are caught at component boundaries and wrapped in ErrorReport structures
2. **Severity Classification**: Errors are classified based on component criticality and impact scope
3. **Deduplication**: Identical errors within 60-second windows are deduplicated to prevent alert storms
4. **Context Preservation**: Full execution context (trace_id, request_id, stack trace) is captured for analysis

### LLM Failure Modes

When the Local_LLM is unavailable or returns malformed responses:

1. **Timeout**: If LLM doesn't respond within 300 seconds, analysis times out and falls back to learning database
2. **Malformed Response**: If response cannot be parsed, a default analysis with low confidence is returned
3. **Unavailable**: If Ollama is not running, the system gracefully degrades to learning-database-only mode
4. **Model Loading**: If configured model cannot be loaded, system attempts to pull from registry or uses fallback model

### Fix Application Failures

When fix application fails:

1. **Atomic Rollback**: All changes are rolled back immediately if any file write fails
2. **Checkpoint Restoration**: System restores to pre-fix state from checkpoint
3. **Status Update**: FixProposal status is updated to REVERTED with rollback reason
4. **Error Analysis**: New error report is generated to understand why fix failed

### Verification Failures

When fix verification fails:

1. **Automatic Rollback**: System triggers rollback to checkpoint
2. **Status Update**: FixProposal status is updated to FAILED
3. **Error Generation**: New error report is created from test failure
4. **Confidence Reduction**: If learned fix fails, confidence score is decremented

---

## Testing Strategy

### Dual Testing Approach

The self-healing deployment system requires both property-based testing and integration testing:

**Property-Based Testing** (100+ iterations each):

- Error deduplication logic
- Severity classification rules
- Unique ID generation
- Confidence score calculations
- Fix ranking algorithms
- Atomic operation semantics
- Checkpoint creation and restoration
- Learning database pattern matching
- Performance latency targets

**Integration Testing** (1-3 representative examples each):

- Ollama/LLM integration and availability
- Test framework integration (pytest)
- File system operations (read/write/delete)
- Checkpoint persistence and recovery
- Learning database persistence
- Monitoring metrics collection
- Alert notification delivery
- Kabbalah component integration

### Unit Test Coverage

Unit tests focus on specific examples and edge cases:

1. **Error Detection**: Capture various exception types, test failures, edge cases
2. **Analysis**: Parse various LLM response formats, handle malformed responses
3. **Fix Generation**: Validate syntax, extract code changes, calculate confidence
4. **Application**: Atomic operations, rollback scenarios, concurrent modification prevention
5. **Verification**: Test selection, status updates, regression detection
6. **Learning**: Pattern matching, similarity scoring, archival logic
7. **Safety**: Critical file detection, dependency checking, API compatibility

### Performance Testing

Performance tests verify latency targets:

1. **Error Detection**: < 10ms for exception capture
2. **LLM Analysis**: < 300s timeout
3. **Fix Generation**: < 5s for fix proposal creation
4. **Fix Application**: < 2s for file changes
5. **Verification**: < 600s for test execution
6. **Learning Database**: < 100ms for queries with 1000+ entries
7. **System Load**: < 20% additional CPU under 100+ errors/minute

### Test Configuration

Each property-based test SHALL:

- Run minimum 100 iterations with randomized inputs
- Include edge cases (empty inputs, boundary values, special characters)
- Verify both success and failure paths
- Include regression detection
- Be tagged with: `Feature: self-healing-deployment, Property {number}: {property_text}`

---

## Error Handling and Recovery

### Rollback Mechanism

The system implements checkpoint-based rollback for safe error recovery:

1. **Checkpoint Creation**: Before applying any fix, all affected files and system state are backed up
2. **Atomic Application**: All file changes are applied as a single atomic operation
3. **Verification**: After application, tests verify the fix resolves the error
4. **Rollback Trigger**: If verification fails, system automatically rolls back to checkpoint
5. **Retention**: Checkpoints are retained for 24 hours, allowing manual rollback if needed

### Concurrent Modification Prevention

The system prevents concurrent fixes to the same files:

1. **File Locking**: When applying a fix, affected files are locked
2. **Queue Management**: Concurrent fix attempts are queued for sequential execution
3. **Timeout**: If lock cannot be acquired within timeout, fix application fails
4. **Audit Logging**: All lock acquisitions and releases are logged

### Safety Constraints

The Safety_Module enforces constraints to prevent breaking changes:

1. **Critical File Protection**: Fixes modifying critical files require manual review
2. **Dependency Validation**: Fixes introducing new dependencies require approval
3. **API Compatibility**: Fixes must maintain backward compatibility
4. **Confidence Threshold**: Fixes with confidence < 0.5 require manual review
5. **Scope Limitation**: Fixes affecting > 5 files require manual review
6. **System State**: During CRITICAL state (multiple errors), automatic fixes are disabled

---

## Deployment Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_URL=http://localhost:11434
LLM_MODEL=llama2
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_TIMEOUT_SECONDS=300

# Learning Database
LEARNING_DB_PATH=/var/lib/self-healing/learning_database.json
LEARNING_DB_BACKUP_PATH=/var/lib/self-healing/backups

# System Configuration
ENVIRONMENT=production  # development, staging, production
ERROR_DETECTION_ENABLED=true
AUTO_FIX_ENABLED=true
MANUAL_REVIEW_REQUIRED_CONFIDENCE_THRESHOLD=0.5
CHECKPOINT_RETENTION_HOURS=24
LEARNING_DB_ARCHIVE_DAYS=30

# Monitoring
METRICS_PORT=9090
ALERT_WEBHOOK_URL=https://alerts.example.com/webhook
ALERT_EMAIL=ops@example.com
AUDIT_LOG_PATH=/var/log/self-healing/audit.log
```

### Configuration File (YAML)

```yaml
self_healing:
  enabled: true

  llm:
    base_url: http://localhost:11434
    model: llama2
    temperature: 0.3
    top_p: 0.9
    top_k: 40
    timeout_seconds: 300
    max_tokens: 2048

  learning_database:
    path: /var/lib/self-healing/learning_database.json
    backup_path: /var/lib/self-healing/backups
    max_entries: 1000
    archive_days: 30

  error_detection:
    enabled: true
    deduplication_window_seconds: 60

  fix_application:
    enabled: true
    atomic_operations: true
    checkpoint_retention_hours: 24
    max_concurrent_fixes: 1

  verification:
    enabled: true
    timeout_seconds: 600

  safety:
    critical_files:
      - config/
      - security/
      - core/orchestration/
    confidence_threshold: 0.5
    max_files_per_fix: 5

  monitoring:
    metrics_enabled: true
    metrics_port: 9090
    audit_logging_enabled: true
    audit_log_path: /var/log/self-healing/audit.log

  environment: production
```

### Initialization Sequence

1. **Load Configuration**: Read environment variables and configuration files
2. **Validate Settings**: Verify all required settings are present and valid
3. **Initialize Learning Database**: Load persisted learning database from disk
4. **Check LLM Availability**: Verify Ollama is running and model is available
5. **Create Directories**: Ensure all required directories exist
6. **Load Error Detection Rules**: Load component-to-severity mappings
7. **Load Test Mappings**: Load component-to-test mappings for verification
8. **Health Check**: Verify all systems are operational
9. **Report Readiness**: Log initialization complete and readiness status

---

## Monitoring and Observability

### Metrics Collection

The system collects comprehensive metrics:

```python
@dataclass
class MonitoringMetrics:
    # Error metrics
    total_errors_detected: int
    errors_by_severity: Dict[str, int]  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    errors_by_component: Dict[str, int]

    # Fix metrics
    total_fixes_generated: int
    total_fixes_applied: int
    total_fixes_verified: int
    total_fixes_failed: int
    total_fixes_reverted: int

    # Performance metrics
    average_detection_time_ms: float
    average_analysis_time_ms: float
    average_fix_generation_time_ms: float
    average_application_time_ms: float
    average_verification_time_ms: float

    # Learning metrics
    learning_database_size: int
    learning_database_queries: int
    average_query_time_ms: float

    # Success rates
    fix_success_rate: float  # verified_fixes / applied_fixes
    learned_fix_success_rate: float

    # Timestamp
    timestamp: datetime
```

### Prometheus Metrics Endpoint

The system exposes metrics in Prometheus format at `/metrics`:

```
# HELP self_healing_errors_total Total errors detected
# TYPE self_healing_errors_total counter
self_healing_errors_total{severity="CRITICAL"} 5
self_healing_errors_total{severity="HIGH"} 12
self_healing_errors_total{severity="MEDIUM"} 23

# HELP self_healing_fixes_applied_total Total fixes applied
# TYPE self_healing_fixes_applied_total counter
self_healing_fixes_applied_total 15

# HELP self_healing_fixes_verified_total Total fixes verified
# TYPE self_healing_fixes_verified_total counter
self_healing_fixes_verified_total 12

# HELP self_healing_detection_latency_ms Error detection latency
# TYPE self_healing_detection_latency_ms histogram
self_healing_detection_latency_ms_bucket{le="10"} 1000
self_healing_detection_latency_ms_bucket{le="50"} 1005
self_healing_detection_latency_ms_bucket{le="+Inf"} 1010

# HELP self_healing_learning_db_size Learning database size
# TYPE self_healing_learning_db_size gauge
self_healing_learning_db_size 342
```

### Audit Logging

All self-healing activities are logged to immutable audit log:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "event_type": "ERROR_DETECTED",
  "error_id": "err-12345",
  "component": "Root_Orchestrator",
  "severity": "CRITICAL",
  "error_type": "DecompositionError",
  "message": "Failed to decompose specification"
}

{
  "timestamp": "2024-01-15T10:30:50.456Z",
  "event_type": "FIX_APPLIED",
  "fix_id": "fix-67890",
  "error_id": "err-12345",
  "files_changed": 2,
  "checkpoint_id": "cp-11111",
  "status": "APPLIED"
}

{
  "timestamp": "2024-01-15T10:31:15.789Z",
  "event_type": "FIX_VERIFIED",
  "fix_id": "fix-67890",
  "tests_passed": 45,
  "tests_failed": 0,
  "status": "VERIFIED"
}

{
  "timestamp": "2024-01-15T10:31:20.012Z",
  "event_type": "FIX_LEARNED",
  "learning_entry_id": "le-22222",
  "error_pattern": "DecompositionError",
  "confidence_score": 0.87
}
```

### Alert Triggers

Critical events trigger alerts:

1. **CRITICAL Error Detected**: Immediate alert for CRITICAL severity errors
2. **Multiple Failures**: Alert if 3+ fixes fail in sequence
3. **LLM Unavailable**: Alert if LLM is unavailable for > 5 minutes
4. **Learning Database Corruption**: Alert if database integrity check fails
5. **System State Inconsistency**: Alert if system state becomes inconsistent

---

## Performance Considerations

### Latency Targets

The system is designed to meet strict latency targets:

| Operation       | Target    | Rationale                              |
| --------------- | --------- | -------------------------------------- |
| Error Detection | < 10ms    | Minimal overhead on exception handling |
| LLM Analysis    | < 300s    | Timeout for LLM inference              |
| Fix Generation  | < 5s      | Quick proposal generation              |
| Fix Application | < 2s      | Atomic file operations                 |
| Verification    | < 600s    | Test suite execution                   |
| Learning Query  | < 100ms   | Database lookup performance            |
| System Load     | < 20% CPU | Minimal impact on main workload        |

### Optimization Strategies

1. **Asynchronous Processing**: Error analysis and fix application run asynchronously
2. **Caching**: Learning database queries are cached for frequently accessed patterns
3. **Batch Operations**: Multiple file changes are batched into single atomic operation
4. **Lazy Loading**: Learning database entries are loaded on-demand
5. **Index Optimization**: Pattern matching uses indexed lookups
6. **Connection Pooling**: LLM connections are pooled for reuse

### Scalability

The system scales to handle:

- 100+ errors per minute with < 50ms detection latency
- 1000+ learning database entries with < 100ms query time
- Concurrent fix applications (queued sequentially)
- Large file changes (multi-MB files)
- Long-running test suites (up to 600 seconds)

---

## Design Decisions and Rationale

### 1. Local LLM Instead of External API

**Decision**: Use Ollama/Llama for local LLM instead of external API (OpenAI, Anthropic)

**Rationale**:

- **Cost**: No per-request API costs; one-time model download
- **Latency**: Local inference eliminates network round-trip
- **Privacy**: Error data never leaves the system
- **Reliability**: No external service dependency
- **Offline Operation**: System works without internet connectivity

### 2. Atomic Fix Application

**Decision**: Apply all file changes atomically (all succeed or all fail)

**Rationale**:

- **Consistency**: System never enters partially-fixed state
- **Safety**: Prevents cascading failures from incomplete fixes
- **Auditability**: Clear before/after states for audit logs
- **Rollback**: Simplifies rollback logic (restore entire checkpoint)

### 3. Learning Database with Persistence

**Decision**: Maintain persistent learning database of successful fixes

**Rationale**:

- **Pattern Reuse**: Similar errors resolved faster on subsequent occurrences
- **Evolution**: System improves over time as more patterns are learned
- **Fallback**: Learning database provides fallback when LLM unavailable
- **Offline Mode**: System can operate in learning-database-only mode

### 4. Checkpoint-Based Rollback

**Decision**: Create checkpoints before fix application for rollback capability

**Rationale**:

- **Safety**: Allows recovery from failed fixes
- **Auditability**: Checkpoint history provides audit trail
- **Simplicity**: Checkpoint restoration is simpler than reverse-engineering undo
- **Retention**: 24-hour retention allows manual rollback if needed

### 5. Confidence-Based Manual Review

**Decision**: Require manual review for low-confidence fixes

**Rationale**:

- **Risk Management**: Prevents application of risky fixes
- **Operator Control**: Humans retain control over critical changes
- **Learning**: Manual review feedback improves confidence scoring
- **Compliance**: Audit trail of manual approvals for compliance

### 6. Deduplication Within Time Window

**Decision**: Deduplicate identical errors within 60-second window

**Rationale**:

- **Alert Storm Prevention**: Prevents overwhelming operators with duplicate alerts
- **Resource Efficiency**: Avoids redundant analysis of same error
- **Occurrence Tracking**: Counter tracks how many times error occurred
- **Pattern Recognition**: Helps identify recurring issues

### 7. Component-Based Severity Classification

**Decision**: Classify severity based on component criticality

**Rationale**:

- **Prioritization**: Critical component errors get immediate attention
- **Automation**: Enables automatic fix application for low-severity errors
- **Consistency**: Standardized severity levels across system
- **Escalation**: Severity can be escalated based on impact scope

---

## Algorithms

### Error Deduplication Algorithm

```
function deduplicate_error(error_report, window_seconds=60):
    # Check if identical error occurred recently
    recent_errors = query_error_history(
        error_type=error_report.error_type,
        message=error_report.message,
        component=error_report.component,
        time_window=window_seconds
    )

    if recent_errors is not empty:
        # Increment counter on most recent occurrence
        most_recent = recent_errors[0]
        most_recent.occurrence_count += 1
        return None  # Don't create new report
    else:
        # New error, create report
        return error_report
```

### Pattern Matching for Similar Errors

```
function find_similar_errors(error_report, top_k=5):
    # Normalize error pattern
    pattern = normalize_error_pattern(
        error_type=error_report.error_type,
        message=error_report.message
    )

    # Query learning database for similar patterns
    candidates = learning_db.query_by_pattern(pattern)

    # Calculate similarity scores
    scored_candidates = []
    for candidate in candidates:
        score = calculate_similarity_score(
            error_report,
            candidate.error_report
        )
        scored_candidates.append((candidate, score))

    # Sort by score and return top-k
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    return scored_candidates[:top_k]

function calculate_similarity_score(error1, error2):
    # Weighted combination of similarity metrics
    type_similarity = 1.0 if error1.error_type == error2.error_type else 0.0
    message_similarity = levenshtein_similarity(error1.message, error2.message)
    component_similarity = 1.0 if error1.component == error2.component else 0.5

    # Weighted average
    score = (
        0.4 * type_similarity +
        0.4 * message_similarity +
        0.2 * component_similarity
    )
    return score
```

### Confidence Score Calculation

```
function calculate_confidence_score(llm_response, learning_context):
    # Base confidence from LLM response
    base_confidence = extract_confidence_from_response(llm_response)

    # Adjust based on learning database context
    if learning_context is not empty:
        # Boost confidence if similar fix exists with high success rate
        similar_fix = learning_context[0]
        success_rate_boost = similar_fix.success_rate * 0.2
        base_confidence = min(1.0, base_confidence + success_rate_boost)

    # Penalize if fix affects many files
    if len(affected_files) > 5:
        base_confidence *= 0.8

    # Penalize if fix modifies critical files
    if has_critical_files(affected_files):
        base_confidence *= 0.7

    return max(0.0, min(1.0, base_confidence))
```

### Fix Ranking Algorithm

```
function rank_fixes(fixes):
    # Sort by confidence score (descending)
    ranked = sorted(fixes, key=lambda f: f.confidence_score, reverse=True)

    # Secondary sort by number of affected files (ascending)
    ranked = sorted(ranked, key=lambda f: len(f.affected_files))

    # Tertiary sort by reasoning length (longer reasoning = more thought)
    ranked = sorted(ranked, key=lambda f: len(f.reasoning), reverse=True)

    return ranked
```

### Rollback Decision Logic

```
function should_rollback(verification_result):
    # Rollback if tests failed
    if verification_result.tests_failed > 0:
        return True

    # Rollback if regressions detected
    if len(verification_result.regressions_detected) > 0:
        return True

    # Rollback if new errors introduced
    if len(verification_result.new_errors) > 0:
        return True

    # Rollback if verification timed out
    if verification_result.timed_out:
        return True

    return False
```

### Learning Database Archival Algorithm

```
function archive_old_entries(older_than_days=30):
    cutoff_date = now() - timedelta(days=older_than_days)

    # Find entries older than cutoff
    old_entries = learning_db.query_by_date(before=cutoff_date)

    # Archive entries
    archived_count = 0
    for entry in old_entries:
        entry.archived = True
        learning_db.update(entry)
        archived_count += 1

    # Maintain searchable index of archived entries
    rebuild_archive_index()

    return archived_count
```

---

## Summary

The Self-Healing Deployment System provides a comprehensive, production-ready framework for autonomous error detection, analysis, and correction in the Kabbalah platform. By combining local LLM analysis with persistent learning, atomic operations with checkpoint-based rollback, and confidence-based manual review, the system enables safe, effective autonomous healing while maintaining operator control and system stability.

Key strengths:

- **Autonomous**: Detects and fixes errors without manual intervention
- **Safe**: Atomic operations, checkpoints, and rollback prevent cascading failures
- **Learning**: Persistent database enables pattern reuse and system evolution
- **Observable**: Comprehensive metrics, audit logs, and alerts provide visibility
- **Performant**: Meets strict latency targets even under high error rates
- **Resilient**: Graceful degradation when LLM unavailable, fallback to learning database
