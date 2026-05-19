"""
Error Analysis Module - Analyzes detected errors using local LLM.

This module analyzes errors using a local LLM (Ollama/Llama) to identify root causes,
suggest fixes, and provide confidence scores. It includes fallback to learning database
when LLM is unavailable, timeout handling, and comprehensive error handling.

Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
"""

import json
import logging
import re
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from kabbalah.llm_local_provider import LocalLLMConfig, LocalLLMProvider
from kabbalah.self_healing_models import ErrorReport, LearningEntry

logger = logging.getLogger(__name__)


@dataclass
class ErrorAnalysis:
    """
    Result of error analysis using LLM or learning database.

    Contains root cause analysis, suggested fixes, affected files, and confidence
    score. Used as input to fix generation module.

    Attributes:
        error_id: ID of the error being analyzed
        root_cause: Root cause analysis text
        suggested_fixes: List of suggested fix descriptions
        affected_files: List of file paths likely affected by error
        confidence_score: Confidence in analysis (0.0-1.0)
        reasoning: Detailed reasoning for the analysis
        llm_model: Name of LLM model used (or "learning_database")
        analysis_time_ms: Time taken to perform analysis
        timestamp: When analysis was performed
        used_learning_database: True if learning database was used instead of LLM

    Requirements: 2.1, 2.3
    """

    error_id: str
    """ID of the error being analyzed"""

    root_cause: str
    """Root cause analysis text"""

    suggested_fixes: List[str]
    """List of suggested fix descriptions"""

    affected_files: List[str]
    """List of file paths likely affected by error"""

    confidence_score: float
    """Confidence in analysis (0.0-1.0)"""

    reasoning: str
    """Detailed reasoning for the analysis"""

    llm_model: str
    """Name of LLM model used (or "learning_database")"""

    analysis_time_ms: float
    """Time taken to perform analysis"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When analysis was performed"""

    used_learning_database: bool = False
    """True if learning database was used instead of LLM"""


class TimeoutException(Exception):
    """Exception raised when LLM analysis times out."""

    pass


class ErrorAnalysisModule:
    """
    Analyzes errors using local LLM with learning database fallback.

    Generates structured analysis prompts, invokes LLM with timeout handling,
    parses responses to extract root cause and suggested fixes, and falls back
    to learning database when LLM is unavailable.

    Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
    """

    def __init__(
        self,
        llm_provider: Optional[LocalLLMProvider] = None,
        llm_config: Optional[LocalLLMConfig] = None,
        learning_database: Optional[List[LearningEntry]] = None,
    ):
        """
        Initialize Error Analysis Module.

        Args:
            llm_provider: LocalLLMProvider instance (created if not provided)
            llm_config: Configuration for LLM (used if provider not provided)
            learning_database: List of LearningEntry objects for fallback

        Requirements: 2.1, 2.2
        """
        self.llm_config = llm_config or LocalLLMConfig()
        self.llm_provider = llm_provider or LocalLLMProvider(self.llm_config)
        self.learning_database = learning_database or []
        self.analysis_history: Dict[str, ErrorAnalysis] = {}

        logger.info(
            f"ErrorAnalysisModule initialized with LLM: {self.llm_config.model} "
            f"at {self.llm_config.base_url}"
        )

    def analyze_error(
        self,
        error_report: ErrorReport,
        learning_context: Optional[List[LearningEntry]] = None,
        timeout_seconds: int = 300,
    ) -> ErrorAnalysis:
        """
        Analyze error using Local_LLM with learning database context.

        Attempts to analyze error using LLM. If LLM is unavailable or times out,
        falls back to learning database. Returns analysis with confidence score.

        Args:
            error_report: ErrorReport to analyze
            learning_context: Optional list of similar learning entries for context
            timeout_seconds: Timeout for LLM analysis (default: 300)

        Returns:
            ErrorAnalysis with root cause, suggested fixes, and confidence

        Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
        """
        start_time = time.time()
        learning_context = learning_context or []

        logger.info(
            f"Analyzing error {error_report.error_id}: {error_report.error_type} "
            f"in {error_report.component}"
        )

        # Try LLM analysis first
        if self.llm_provider.available:
            try:
                analysis = self._analyze_with_llm(
                    error_report, learning_context, timeout_seconds
                )
                # Note: analysis_time_ms is already set in _analyze_with_llm
                self.analysis_history[error_report.error_id] = analysis
                logger.info(
                    f"LLM analysis completed for {error_report.error_id} "
                    f"in {analysis.analysis_time_ms:.0f}ms with confidence {analysis.confidence_score:.2f}"
                )
                return analysis
            except TimeoutException:
                logger.warning(
                    f"LLM analysis timed out for {error_report.error_id}, "
                    f"falling back to learning database"
                )
            except Exception as e:
                logger.warning(
                    f"LLM analysis failed for {error_report.error_id}: {str(e)}, "
                    f"falling back to learning database"
                )
        else:
            logger.warning(
                f"LLM unavailable for {error_report.error_id}, "
                f"using learning database fallback"
            )

        # Fallback to learning database
        analysis = self._analyze_with_learning_database(error_report, learning_context)
        analysis_time_ms = (time.time() - start_time) * 1000
        analysis.analysis_time_ms = analysis_time_ms
        self.analysis_history[error_report.error_id] = analysis

        logger.info(
            f"Learning database analysis completed for {error_report.error_id} "
            f"in {analysis_time_ms:.0f}ms with confidence {analysis.confidence_score:.2f}"
        )

        return analysis

    def _analyze_with_llm(
        self,
        error_report: ErrorReport,
        learning_context: List[LearningEntry],
        timeout_seconds: int,
    ) -> ErrorAnalysis:
        """
        Analyze error using Local_LLM.

        Generates analysis prompt, invokes LLM with timeout, and parses response.

        Args:
            error_report: ErrorReport to analyze
            learning_context: Similar learning entries for context
            timeout_seconds: Timeout for LLM invocation

        Returns:
            ErrorAnalysis from LLM response

        Raises:
            TimeoutException: If LLM doesn't respond within timeout
            Exception: If LLM response is malformed

        Requirements: 2.1, 2.2, 2.3
        """
        start_time = time.time()
        
        # Generate analysis prompt
        prompt = self.generate_analysis_prompt(error_report, learning_context)

        logger.debug(f"Generated analysis prompt for {error_report.error_id}")

        # Invoke LLM with timeout
        try:
            response = self._invoke_llm_with_timeout(prompt, timeout_seconds)
        except TimeoutException:
            raise

        logger.debug(f"Received LLM response for {error_report.error_id}")

        # Parse LLM response
        try:
            root_cause, suggested_fixes, affected_files, confidence = (
                self.parse_llm_response(response)
            )
        except Exception as e:
            logger.error(
                f"Failed to parse LLM response for {error_report.error_id}: {str(e)}"
            )
            # Return default analysis with low confidence
            analysis_time_ms = (time.time() - start_time) * 1000
            return ErrorAnalysis(
                error_id=error_report.error_id,
                root_cause="Unable to parse LLM response",
                suggested_fixes=[],
                affected_files=[],
                confidence_score=0.2,
                reasoning=f"LLM response parsing failed: {str(e)}",
                llm_model=self.llm_config.model,
                analysis_time_ms=analysis_time_ms,
                used_learning_database=False,
            )

        # Build reasoning
        reasoning = self._build_reasoning(
            error_report, root_cause, suggested_fixes, learning_context
        )

        analysis_time_ms = (time.time() - start_time) * 1000
        return ErrorAnalysis(
            error_id=error_report.error_id,
            root_cause=root_cause,
            suggested_fixes=suggested_fixes,
            affected_files=affected_files,
            confidence_score=confidence,
            reasoning=reasoning,
            llm_model=self.llm_config.model,
            analysis_time_ms=analysis_time_ms,
            used_learning_database=False,
        )

    def _analyze_with_learning_database(
        self,
        error_report: ErrorReport,
        learning_context: Optional[List[LearningEntry]] = None,
    ) -> ErrorAnalysis:
        """
        Analyze error using learning database fallback.

        Searches learning database for similar patterns and returns analysis
        based on best match.

        Args:
            error_report: ErrorReport to analyze
            learning_context: Optional list of similar learning entries

        Returns:
            ErrorAnalysis from learning database

        Requirements: 2.4, 2.6
        """
        learning_context = learning_context or []

        if not learning_context:
            # No similar patterns found
            logger.warning(
                f"No similar patterns found in learning database for {error_report.error_id}"
            )
            return ErrorAnalysis(
                error_id=error_report.error_id,
                root_cause="No similar patterns found in learning database",
                suggested_fixes=[],
                affected_files=[],
                confidence_score=0.1,
                reasoning="Learning database is empty or no similar patterns found",
                llm_model="learning_database",
                analysis_time_ms=0.0,
                used_learning_database=True,
            )

        # Use best match from learning context
        best_match = learning_context[0]

        # Extract information from best match
        suggested_fixes = [best_match.fix_description]
        affected_files = [change.file_path for change in best_match.code_changes]

        # Adjust confidence based on success rate
        confidence = best_match.success_rate * 0.9  # Slightly lower than stored confidence

        reasoning = (
            f"Based on similar pattern from learning database: {best_match.error_pattern}. "
            f"This fix has been applied {best_match.usage_count} times with "
            f"{best_match.success_count} successes ({best_match.success_rate:.1%} success rate)."
        )

        return ErrorAnalysis(
            error_id=error_report.error_id,
            root_cause=best_match.reasoning,
            suggested_fixes=suggested_fixes,
            affected_files=affected_files,
            confidence_score=confidence,
            reasoning=reasoning,
            llm_model="learning_database",
            analysis_time_ms=0.0,  # Set by caller
            used_learning_database=True,
        )

    def generate_analysis_prompt(
        self,
        error_report: ErrorReport,
        similar_fixes: Optional[List[LearningEntry]] = None,
    ) -> str:
        """
        Generate structured analysis prompt for LLM.

        Creates a detailed prompt containing error information, stack trace,
        and context from similar patterns in learning database.

        Args:
            error_report: ErrorReport to analyze
            similar_fixes: Optional list of similar fixes from learning database

        Returns:
            Structured analysis prompt for LLM

        Requirements: 2.1, 2.6
        """
        similar_fixes = similar_fixes or []

        prompt = f"""Analyze this error and provide root cause analysis and suggested fixes.

ERROR INFORMATION:
- Error Type: {error_report.error_type}
- Message: {error_report.message}
- Component: {error_report.component}
- Severity: {error_report.severity.value}
- File: {error_report.file_path}:{error_report.line_number}
- Occurrence Count: {error_report.occurrence_count}

STACK TRACE:
{error_report.stack_trace}

EXECUTION CONTEXT:
{json.dumps(error_report.context, indent=2)}
"""

        # Add similar patterns from learning database if available
        if similar_fixes:
            prompt += "\nSIMILAR PATTERNS FROM LEARNING DATABASE:\n"
            for i, fix in enumerate(similar_fixes[:3], 1):
                prompt += f"\nPattern {i}:\n"
                prompt += f"- Error Type: {fix.error_type}\n"
                prompt += f"- Pattern: {fix.error_message_pattern}\n"
                prompt += f"- Fix: {fix.fix_description}\n"
                prompt += f"- Success Rate: {fix.success_rate:.1%}\n"
                prompt += f"- Reasoning: {fix.reasoning}\n"

        prompt += """
ANALYSIS REQUIRED:
1. Root Cause: What is the underlying cause of this error?
2. Suggested Fixes: What are 1-3 specific fixes to address the root cause?
3. Affected Files: Which files are likely affected by this error?
4. Confidence: How confident are you in this analysis (0.0-1.0)?

RESPONSE FORMAT:
Provide your response as JSON with this structure:
{
    "root_cause": "Detailed root cause analysis",
    "suggested_fixes": [
        "Fix 1 description",
        "Fix 2 description"
    ],
    "affected_files": [
        "path/to/file1.py",
        "path/to/file2.py"
    ],
    "confidence": 0.85,
    "reasoning": "Detailed reasoning for the analysis"
}
"""

        return prompt

    def parse_llm_response(self, response: str) -> Tuple[str, List[str], List[str], float]:
        """
        Parse LLM response to extract analysis components.

        Extracts root cause, suggested fixes, affected files, and confidence score
        from LLM response. Handles both JSON and text formats.

        Args:
            response: LLM response text

        Returns:
            Tuple of (root_cause, suggested_fixes, affected_files, confidence_score)

        Raises:
            Exception: If response cannot be parsed

        Requirements: 2.3, 2.5
        """
        # Try to extract JSON from response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group())

                root_cause = data.get("root_cause", "")
                suggested_fixes = data.get("suggested_fixes", [])
                affected_files = data.get("affected_files", [])
                confidence = float(data.get("confidence", 0.5))

                # Validate confidence is in bounds
                confidence = max(0.0, min(1.0, confidence))

                # Ensure lists are not None
                suggested_fixes = suggested_fixes or []
                affected_files = affected_files or []

                logger.debug(
                    f"Parsed LLM response: confidence={confidence}, "
                    f"fixes={len(suggested_fixes)}, files={len(affected_files)}"
                )

                return root_cause, suggested_fixes, affected_files, confidence

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
                raise Exception(f"Invalid JSON in LLM response: {str(e)}")

        else:
            # No JSON found in response
            logger.error("No JSON found in LLM response")
            raise Exception("LLM response does not contain valid JSON")

    def _invoke_llm_with_timeout(
        self, prompt: str, timeout_seconds: int
    ) -> str:
        """
        Invoke LLM with timeout handling.

        Calls LLM provider with timeout. Raises TimeoutException if LLM
        doesn't respond within timeout.

        Args:
            prompt: Analysis prompt for LLM
            timeout_seconds: Timeout in seconds

        Returns:
            LLM response text

        Raises:
            TimeoutException: If LLM doesn't respond within timeout

        Requirements: 2.2
        """
        # Set timeout using signal (Unix-like systems)
        def timeout_handler(signum, frame):
            raise TimeoutException(
                f"LLM analysis timed out after {timeout_seconds} seconds"
            )

        # Note: signal.signal only works on Unix-like systems
        # For cross-platform support, we use a simpler approach with time tracking
        start_time = time.time()

        try:
            response = self.llm_provider.analyze(prompt)

            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutException(
                    f"LLM analysis exceeded timeout of {timeout_seconds} seconds "
                    f"(took {elapsed_time:.1f}s)"
                )

            if not response:
                raise Exception("LLM returned empty response")

            return response

        except TimeoutException:
            raise
        except Exception as e:
            raise Exception(f"LLM invocation failed: {str(e)}")

    def _build_reasoning(
        self,
        error_report: ErrorReport,
        root_cause: str,
        suggested_fixes: List[str],
        learning_context: List[LearningEntry],
    ) -> str:
        """
        Build detailed reasoning for the analysis.

        Combines root cause analysis with context from learning database
        and error report details.

        Args:
            error_report: Original error report
            root_cause: Root cause analysis from LLM
            suggested_fixes: Suggested fixes from LLM
            learning_context: Similar patterns from learning database

        Returns:
            Detailed reasoning text
        """
        reasoning = f"Error Analysis for {error_report.error_type} in {error_report.component}:\n\n"
        reasoning += f"Root Cause: {root_cause}\n\n"
        reasoning += f"Suggested Fixes ({len(suggested_fixes)}):\n"

        for i, fix in enumerate(suggested_fixes, 1):
            reasoning += f"  {i}. {fix}\n"

        if learning_context:
            reasoning += f"\nLearning Database Context:\n"
            reasoning += f"  Found {len(learning_context)} similar pattern(s)\n"
            best_match = learning_context[0]
            reasoning += (
                f"  Best match: {best_match.error_pattern} "
                f"({best_match.success_rate:.1%} success rate)\n"
            )

        return reasoning

    def get_analysis_history(self) -> Dict[str, ErrorAnalysis]:
        """
        Get history of all analyses performed.

        Returns:
            Dict mapping error_id to ErrorAnalysis
        """
        return self.analysis_history.copy()

    def clear_analysis_history(self) -> None:
        """Clear analysis history."""
        self.analysis_history.clear()
        logger.info("Analysis history cleared")

    def set_learning_database(self, learning_database: List[LearningEntry]) -> None:
        """
        Set the learning database for fallback analysis.

        Args:
            learning_database: List of LearningEntry objects
        """
        self.learning_database = learning_database
        logger.info(f"Learning database updated with {len(learning_database)} entries")
