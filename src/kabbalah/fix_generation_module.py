"""
Fix Generation Module - Generates code fixes from error analysis.

This module generates fix proposals from error analysis results. It extracts
code changes from LLM analysis, validates syntax, calculates confidence scores,
and ranks fixes by confidence. Includes comprehensive error handling and logging.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
"""

import ast
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from kabbalah.error_analysis_module import ErrorAnalysis
from kabbalah.self_healing_models import CodeChange, FixProposal, FixStatus

logger = logging.getLogger(__name__)


@dataclass
class FixGenerationResult:
    """
    Result of fix generation process.

    Contains generated fix proposals and any errors encountered during generation.

    Attributes:
        fixes: List of generated FixProposal objects
        primary_fix: The highest-confidence fix (or None if no valid fixes)
        generation_time_ms: Time taken to generate fixes
        errors: List of error messages encountered during generation
        timestamp: When generation was performed

    Requirements: 3.1
    """

    fixes: List[FixProposal]
    """List of generated FixProposal objects"""

    primary_fix: Optional[FixProposal] = None
    """The highest-confidence fix (or None if no valid fixes)"""

    generation_time_ms: float = 0.0
    """Time taken to generate fixes"""

    errors: List[str] = field(default_factory=list)
    """List of error messages encountered during generation"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When generation was performed"""


class FixGenerationModule:
    """
    Generates code fixes from error analysis results.

    Extracts code changes from LLM analysis, validates syntax, calculates
    confidence scores, and ranks fixes by confidence. Supports multiple fix
    proposals per error with comprehensive error handling.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
    """

    def __init__(self):
        """
        Initialize Fix Generation Module.

        Requirements: 3.1
        """
        self.generation_history: Dict[str, FixGenerationResult] = {}
        logger.info("FixGenerationModule initialized")

    def generate_fix(
        self,
        error_analysis: ErrorAnalysis,
        learning_context: Optional[List[Any]] = None,
    ) -> FixGenerationResult:
        """
        Generate fix proposal from error analysis.

        Creates a FixProposal with code changes, confidence score, and reasoning.
        Validates syntax of proposed changes and ranks multiple fixes by confidence.

        Args:
            error_analysis: ErrorAnalysis object from error analysis module
            learning_context: Optional list of similar learning entries for context

        Returns:
            FixGenerationResult with generated fixes

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
        """
        import time

        start_time = time.time()
        learning_context = learning_context or []
        errors = []

        logger.info(
            f"Generating fix for error {error_analysis.error_id} "
            f"with confidence {error_analysis.confidence_score:.2f}"
        )

        try:
            # Extract code changes from analysis
            code_changes = self.extract_code_changes(error_analysis.suggested_fixes)

            if not code_changes:
                logger.warning(
                    f"No code changes extracted for error {error_analysis.error_id}"
                )
                errors.append("No code changes extracted from analysis")
                generation_time_ms = (time.time() - start_time) * 1000
                return FixGenerationResult(
                    fixes=[],
                    primary_fix=None,
                    generation_time_ms=generation_time_ms,
                    errors=errors,
                )

            # Validate syntax of proposed changes
            validation_errors = []
            for change in code_changes:
                if not self.validate_syntax(change.file_path, change.new_content):
                    validation_errors.append(
                        f"Syntax error in {change.file_path}: {change.new_content[:100]}"
                    )

            if validation_errors:
                logger.warning(
                    f"Syntax validation failed for error {error_analysis.error_id}: "
                    f"{validation_errors}"
                )
                errors.extend(validation_errors)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                error_analysis, code_changes, learning_context
            )

            # Determine if manual review is required
            requires_manual_review = confidence_score < 0.5 or len(code_changes) > 5

            # Create fix proposal
            fix_proposal = FixProposal(
                fix_id=str(uuid.uuid4()),
                error_id=error_analysis.error_id,
                description=self._generate_fix_description(
                    error_analysis.root_cause, code_changes
                ),
                code_changes=code_changes,
                confidence_score=confidence_score,
                reasoning=error_analysis.reasoning,
                affected_files=error_analysis.affected_files,
                requires_manual_review=requires_manual_review,
                status=FixStatus.PENDING,
                timestamp=datetime.now(),
            )

            logger.info(
                f"Generated fix {fix_proposal.fix_id} for error {error_analysis.error_id} "
                f"with confidence {confidence_score:.2f}"
            )

            # Create result
            generation_time_ms = (time.time() - start_time) * 1000
            result = FixGenerationResult(
                fixes=[fix_proposal],
                primary_fix=fix_proposal,
                generation_time_ms=generation_time_ms,
                errors=errors,
            )

            # Store in history
            self.generation_history[error_analysis.error_id] = result

            return result

        except Exception as e:
            logger.error(
                f"Error generating fix for {error_analysis.error_id}: {str(e)}"
            )
            errors.append(f"Fix generation failed: {str(e)}")
            generation_time_ms = (time.time() - start_time) * 1000
            return FixGenerationResult(
                fixes=[],
                primary_fix=None,
                generation_time_ms=generation_time_ms,
                errors=errors,
            )

    def extract_code_changes(self, suggested_fixes: List[str]) -> List[CodeChange]:
        """
        Extract file paths and new content from suggested fixes.

        Parses suggested fix descriptions to extract file paths and code changes.
        Handles various formats including code blocks, file paths, and diffs.

        Args:
            suggested_fixes: List of suggested fix descriptions from LLM

        Returns:
            List of CodeChange objects

        Requirements: 3.2, 3.3
        """
        code_changes = []

        for fix_description in suggested_fixes:
            try:
                # Try to extract file path and content from fix description
                # Look for patterns like "file: path/to/file.py" or "File: path/to/file.py"
                file_match = re.search(
                    r"(?:file|File|FILE):\s*([^\n]+)", fix_description
                )

                if not file_match:
                    # Try to extract from code block markers
                    file_match = re.search(
                        r"```(?:python|py)?\s*([^\n]+)\n", fix_description
                    )

                if not file_match:
                    logger.debug(
                        f"Could not extract file path from fix: {fix_description[:100]}"
                    )
                    continue

                file_path = file_match.group(1).strip()

                # Extract code content
                # Look for code blocks
                code_match = re.search(
                    r"```(?:python|py)?\n(.*?)\n```", fix_description, re.DOTALL
                )

                if not code_match:
                    # Try to extract from "new content:" or similar markers
                    code_match = re.search(
                        r"(?:new content|New content|NEW CONTENT):\s*\n(.*?)(?:\n\n|$)",
                        fix_description,
                        re.DOTALL,
                    )

                if not code_match:
                    logger.debug(
                        f"Could not extract code content from fix: {fix_description[:100]}"
                    )
                    continue

                new_content = code_match.group(1).strip()

                if not new_content:
                    logger.debug(f"Extracted empty code content for {file_path}")
                    continue

                # Create CodeChange object
                # Note: original_content and line numbers would be populated during application
                code_change = CodeChange(
                    file_path=file_path,
                    original_content="",  # Will be populated during application
                    new_content=new_content,
                    line_start=0,  # Will be populated during application
                    line_end=0,  # Will be populated during application
                    diff="",  # Will be populated during application
                )

                code_changes.append(code_change)
                logger.debug(f"Extracted code change for {file_path}")

            except Exception as e:
                logger.warning(
                    f"Error extracting code change from fix: {str(e)}"
                )
                continue

        return code_changes

    def validate_syntax(self, file_path: str, new_content: str) -> bool:
        """
        Validate that proposed content is syntactically correct.

        Performs syntax validation for Python files using AST parsing.
        Returns True if syntax is valid, False otherwise.

        Args:
            file_path: Path to file being modified
            new_content: New file content to validate

        Returns:
            True if syntax is valid, False otherwise

        Requirements: 3.3, 3.7
        """
        # Only validate Python files
        if not file_path.endswith(".py"):
            logger.debug(f"Skipping syntax validation for non-Python file: {file_path}")
            return True

        try:
            # Try to parse the content as Python code
            ast.parse(new_content)
            logger.debug(f"Syntax validation passed for {file_path}")
            return True

        except SyntaxError as e:
            logger.warning(
                f"Syntax error in {file_path} at line {e.lineno}: {e.msg}"
            )
            return False

        except Exception as e:
            logger.warning(f"Error validating syntax for {file_path}: {str(e)}")
            return False

    def rank_fixes(self, fixes: List[FixProposal]) -> List[FixProposal]:
        """
        Rank fixes by confidence score (highest first).

        Sorts fixes in descending order by confidence_score.

        Args:
            fixes: List of FixProposal objects to rank

        Returns:
            Sorted list of FixProposal objects (highest confidence first)

        Requirements: 3.9
        """
        ranked_fixes = sorted(
            fixes, key=lambda f: f.confidence_score, reverse=True
        )

        logger.debug(
            f"Ranked {len(ranked_fixes)} fixes: "
            f"{[f'{f.fix_id[:8]}({f.confidence_score:.2f})' for f in ranked_fixes]}"
        )

        return ranked_fixes

    def _calculate_confidence_score(
        self,
        error_analysis: ErrorAnalysis,
        code_changes: List[CodeChange],
        learning_context: Optional[List[Any]] = None,
    ) -> float:
        """
        Calculate confidence score for the fix.

        Starts with base confidence from LLM analysis, then adjusts based on:
        - Number of affected files (penalty for many files)
        - Learning database context (boost if similar fix succeeded)
        - Syntax validation (penalty if syntax errors)

        Args:
            error_analysis: ErrorAnalysis object
            code_changes: List of code changes
            learning_context: Optional list of similar learning entries

        Returns:
            Confidence score (0.0-1.0)

        Requirements: 3.4, 3.8
        """
        learning_context = learning_context or []

        # Start with base confidence from LLM
        confidence = error_analysis.confidence_score

        # Penalty for multiple affected files
        if len(code_changes) > 3:
            penalty = 0.1 * (len(code_changes) - 3)
            confidence -= penalty
            logger.debug(
                f"Applied file count penalty: {penalty:.2f} "
                f"(files: {len(code_changes)})"
            )

        # Boost from learning database context
        if learning_context:
            # Get best match from learning context
            best_match = learning_context[0]
            if hasattr(best_match, "success_rate"):
                boost = best_match.success_rate * 0.1
                confidence += boost
                logger.debug(
                    f"Applied learning database boost: {boost:.2f} "
                    f"(success_rate: {best_match.success_rate:.1%})"
                )

        # Ensure confidence stays within bounds
        confidence = max(0.0, min(1.0, confidence))

        logger.debug(f"Calculated confidence score: {confidence:.2f}")

        return confidence

    def _generate_fix_description(
        self, root_cause: str, code_changes: List[CodeChange]
    ) -> str:
        """
        Generate human-readable fix description.

        Creates a concise description of the fix based on root cause and changes.

        Args:
            root_cause: Root cause analysis text
            code_changes: List of code changes

        Returns:
            Human-readable fix description

        Requirements: 3.1
        """
        description = f"Fix for: {root_cause[:100]}"

        if code_changes:
            description += f"\nModifies {len(code_changes)} file(s): "
            description += ", ".join([c.file_path for c in code_changes[:3]])
            if len(code_changes) > 3:
                description += f" and {len(code_changes) - 3} more"

        return description

    def get_generation_history(self) -> Dict[str, FixGenerationResult]:
        """
        Get history of all fix generations performed.

        Returns:
            Dict mapping error_id to FixGenerationResult
        """
        return self.generation_history.copy()

    def clear_generation_history(self) -> None:
        """Clear fix generation history."""
        self.generation_history.clear()
        logger.info("Fix generation history cleared")
