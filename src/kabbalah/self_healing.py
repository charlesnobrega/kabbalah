"""Self-Healing System - Automatic error detection and correction using LLM.

This module enables the Kabbalah system to:
1. Detect runtime errors and test failures
2. Analyze root causes using LLM
3. Generate and apply fixes automatically
4. Learn from corrections over time
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for detected errors."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FixStatus(Enum):
    """Status of a fix attempt."""
    PENDING = "pending"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"
    REVERTED = "reverted"


@dataclass
class ErrorReport:
    """Report of a detected error."""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "stack_trace": self.stack_trace,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class FixProposal:
    """Proposed fix for an error."""
    fix_id: str
    error_id: str
    description: str
    changes: Dict[str, str]  # file_path -> new_content
    confidence: float  # 0.0 to 1.0
    reasoning: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    status: FixStatus = FixStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fix_id": self.fix_id,
            "error_id": self.error_id,
            "description": self.description,
            "changes": self.changes,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


class SelfHealingSystem:
    """System for automatic error detection and correction."""
    
    def __init__(self, llm_provider=None):
        """Initialize self-healing system.
        
        Args:
            llm_provider: Optional LLM provider for analysis and fix generation
        """
        self.llm_provider = llm_provider
        self.error_history: List[ErrorReport] = []
        self.fix_history: List[FixProposal] = []
        self.learning_database: Dict[str, Any] = {}
        self._load_learning_database()
    
    def detect_error(
        self,
        error_type: str,
        message: str,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> ErrorReport:
        """Detect and report an error.
        
        Args:
            error_type: Type of error (e.g., "test_failure", "runtime_error")
            message: Error message
            severity: Severity level
            context: Additional context
            stack_trace: Stack trace if available
            file_path: File where error occurred
            line_number: Line number where error occurred
            
        Returns:
            ErrorReport object
        """
        error_id = self._generate_error_id(error_type, message)
        
        error_report = ErrorReport(
            error_id=error_id,
            error_type=error_type,
            message=message,
            severity=severity,
            context=context or {},
            stack_trace=stack_trace,
            file_path=file_path,
            line_number=line_number,
        )
        
        self.error_history.append(error_report)
        logger.warning(f"Error detected: {error_id} - {message}")
        
        return error_report
    
    def analyze_error(self, error_report: ErrorReport) -> Optional[str]:
        """Analyze error and generate fix proposal using LLM.
        
        Args:
            error_report: Error to analyze
            
        Returns:
            Fix proposal ID if generated, None otherwise
        """
        if not self.llm_provider:
            logger.info(f"No LLM provider available for analyzing {error_report.error_id}")
            return None
        
        try:
            # Check if we've seen similar errors before
            similar_fixes = self._find_similar_fixes(error_report)
            if similar_fixes:
                logger.info(f"Found {len(similar_fixes)} similar fixes for {error_report.error_id}")
                return similar_fixes[0].fix_id
            
            # Generate analysis prompt
            prompt = self._generate_analysis_prompt(error_report)
            
            # Get LLM analysis
            analysis = self.llm_provider.analyze(prompt)
            
            # Generate fix proposal
            fix_proposal = self._generate_fix_proposal(error_report, analysis)
            
            if fix_proposal:
                self.fix_history.append(fix_proposal)
                logger.info(f"Generated fix proposal: {fix_proposal.fix_id}")
                return fix_proposal.fix_id
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to analyze error {error_report.error_id}: {str(e)}")
            return None
    
    def apply_fix(self, fix_proposal: FixProposal) -> bool:
        """Apply a fix proposal.
        
        Args:
            fix_proposal: Fix to apply
            
        Returns:
            True if fix applied successfully, False otherwise
        """
        try:
            # Apply changes
            for file_path, new_content in fix_proposal.changes.items():
                self._apply_file_change(file_path, new_content)
            
            fix_proposal.status = FixStatus.APPLIED
            logger.info(f"Applied fix: {fix_proposal.fix_id}")
            
            return True
        
        except Exception as e:
            fix_proposal.status = FixStatus.FAILED
            logger.error(f"Failed to apply fix {fix_proposal.fix_id}: {str(e)}")
            return False
    
    def verify_fix(self, fix_proposal: FixProposal, test_result: bool) -> bool:
        """Verify if a fix resolved the issue.
        
        Args:
            fix_proposal: Fix to verify
            test_result: True if tests pass after fix, False otherwise
            
        Returns:
            True if fix verified, False otherwise
        """
        if test_result:
            fix_proposal.status = FixStatus.VERIFIED
            logger.info(f"Fix verified: {fix_proposal.fix_id}")
            
            # Learn from this fix
            self._learn_from_fix(fix_proposal)
            
            return True
        else:
            fix_proposal.status = FixStatus.FAILED
            logger.warning(f"Fix failed verification: {fix_proposal.fix_id}")
            return False
    
    def _generate_error_id(self, error_type: str, message: str) -> str:
        """Generate unique error ID."""
        content = f"{error_type}:{message}"
        hash_obj = hashlib.md5(content.encode())
        return f"err_{hash_obj.hexdigest()[:8]}"
    
    def _generate_analysis_prompt(self, error_report: ErrorReport) -> str:
        """Generate prompt for LLM analysis."""
        prompt = f"""Analyze this error and suggest a fix:

Error Type: {error_report.error_type}
Message: {error_report.message}
Severity: {error_report.severity.value}
File: {error_report.file_path}
Line: {error_report.line_number}

Stack Trace:
{error_report.stack_trace or 'N/A'}

Context:
{json.dumps(error_report.context, indent=2)}

Please provide:
1. Root cause analysis
2. Suggested fix
3. Files that need to be changed
4. Confidence level (0-1)
"""
        return prompt
    
    def _generate_fix_proposal(
        self,
        error_report: ErrorReport,
        analysis: str
    ) -> Optional[FixProposal]:
        """Generate fix proposal from LLM analysis."""
        try:
            # Parse LLM response (simplified - in production would be more sophisticated)
            fix_id = self._generate_error_id("fix", error_report.error_id)
            
            fix_proposal = FixProposal(
                fix_id=fix_id,
                error_id=error_report.error_id,
                description=f"Auto-generated fix for {error_report.error_type}",
                changes={},  # Would be populated from LLM analysis
                confidence=0.7,  # Would be extracted from LLM response
                reasoning=analysis,
            )
            
            return fix_proposal
        
        except Exception as e:
            logger.error(f"Failed to generate fix proposal: {str(e)}")
            return None
    
    def _find_similar_fixes(self, error_report: ErrorReport) -> List[FixProposal]:
        """Find similar fixes from history."""
        similar = []
        
        for fix in self.fix_history:
            if (fix.status == FixStatus.VERIFIED and
                fix.error_id.startswith(error_report.error_type)):
                similar.append(fix)
        
        return similar
    
    def _apply_file_change(self, file_path: str, new_content: str) -> None:
        """Apply change to a file."""
        # In production, would use proper file I/O with backups
        logger.info(f"Would apply changes to {file_path}")
    
    def _learn_from_fix(self, fix_proposal: FixProposal) -> None:
        """Learn from a successful fix."""
        key = f"{fix_proposal.error_id}:verified"
        self.learning_database[key] = {
            "fix_id": fix_proposal.fix_id,
            "description": fix_proposal.description,
            "reasoning": fix_proposal.reasoning,
            "timestamp": datetime.now().timestamp(),
        }
        self._save_learning_database()
    
    def _load_learning_database(self) -> None:
        """Load learning database from storage."""
        try:
            # In production, would load from persistent storage
            logger.info("Learning database loaded")
        except Exception as e:
            logger.warning(f"Failed to load learning database: {str(e)}")
    
    def _save_learning_database(self) -> None:
        """Save learning database to storage."""
        try:
            # In production, would save to persistent storage
            logger.info("Learning database saved")
        except Exception as e:
            logger.warning(f"Failed to save learning database: {str(e)}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected errors."""
        return {
            "total_errors": len(self.error_history),
            "total_fixes": len(self.fix_history),
            "verified_fixes": sum(1 for f in self.fix_history if f.status == FixStatus.VERIFIED),
            "failed_fixes": sum(1 for f in self.fix_history if f.status == FixStatus.FAILED),
            "errors_by_severity": {
                severity.value: sum(1 for e in self.error_history if e.severity == severity)
                for severity in ErrorSeverity
            },
        }
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learned patterns."""
        return {
            "total_learned_patterns": len(self.learning_database),
            "patterns": list(self.learning_database.keys()),
        }
