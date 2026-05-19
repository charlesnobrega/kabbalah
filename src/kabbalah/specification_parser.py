"""
Specification Parser

Parses and validates specifications from JSON/YAML formats.
"""

import json
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SpecificationFormat(Enum):
    """Supported specification formats"""
    JSON = "json"
    YAML = "yaml"


class ParsingError(Exception):
    """Raised when specification parsing fails"""
    pass


class ValidationError(Exception):
    """Raised when specification validation fails"""
    pass


@dataclass
class ParseResult:
    """Result of parsing a specification"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    format: Optional[SpecificationFormat] = None
    version: Optional[str] = None


class SpecificationParser:
    """
    Parses and validates specifications from JSON/YAML formats.
    
    Features:
    - Support for JSON and YAML formats
    - Automatic format detection
    - Comprehensive validation
    - Versioning support
    - Descriptive error messages
    """
    
    # Required fields for a valid specification
    REQUIRED_FIELDS = {
        "run_id",
        "project_name",
        "project_description",
        "scope",
        "domains",
        "dependencies",
        "created_at",
        "version",
    }
    
    # Supported versions
    SUPPORTED_VERSIONS = {"1.0"}
    
    def __init__(self):
        """Initialize the specification parser"""
        self.last_parsed_format: Optional[SpecificationFormat] = None
        self.last_parsed_version: Optional[str] = None
    
    def parse(
        self,
        content: Union[str, Dict[str, Any]],
        format: Optional[SpecificationFormat] = None,
    ) -> ParseResult:
        """
        Parse a specification from string or dictionary.
        
        Args:
            content: Specification content (JSON string, YAML string, or dict)
            format: Format hint (auto-detected if not provided)
            
        Returns:
            ParseResult with parsed data or error
        """
        try:
            # If already a dict, validate directly
            if isinstance(content, dict):
                data = content
                detected_format = SpecificationFormat.JSON
            else:
                # Try to detect format and parse
                data, detected_format = self._parse_content(content, format)
            
            # Validate the parsed data
            self._validate_specification(data)
            
            # Extract version
            version = data.get("version", "1.0")
            
            # Store metadata
            self.last_parsed_format = detected_format
            self.last_parsed_version = version
            
            logger.debug(f"Successfully parsed specification (version {version})")
            
            return ParseResult(
                success=True,
                data=data,
                format=detected_format,
                version=version,
            )
        
        except (ParsingError, ValidationError) as e:
            logger.error(f"Specification parsing failed: {str(e)}")
            return ParseResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {str(e)}")
            return ParseResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )
    
    def _parse_content(
        self,
        content: str,
        format: Optional[SpecificationFormat] = None,
    ) -> tuple[Dict[str, Any], SpecificationFormat]:
        """
        Parse content string to dictionary.
        
        Args:
            content: Content string
            format: Format hint
            
        Returns:
            Tuple of (parsed_data, detected_format)
        """
        if format:
            # Use specified format
            if format == SpecificationFormat.JSON:
                return self._parse_json(content), format
            elif format == SpecificationFormat.YAML:
                return self._parse_yaml(content), format
            else:
                raise ParsingError(f"Unsupported format: {format}")
        
        # Try to auto-detect format
        # First try JSON
        try:
            data = self._parse_json(content)
            return data, SpecificationFormat.JSON
        except ParsingError:
            pass
        
        # Then try YAML
        try:
            data = self._parse_yaml(content)
            return data, SpecificationFormat.YAML
        except ParsingError:
            pass
        
        raise ParsingError(
            "Could not parse content as JSON or YAML. "
            "Please provide valid JSON or YAML format."
        )
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON content.
        
        Args:
            content: JSON string
            
        Returns:
            Parsed dictionary
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON: {str(e)}")
    
    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML content.
        
        Args:
            content: YAML string
            
        Returns:
            Parsed dictionary
        """
        try:
            import yaml
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise ParsingError("YAML content must be a dictionary")
            return data
        except ImportError:
            raise ParsingError("YAML support requires PyYAML to be installed")
        except Exception as e:
            raise ParsingError(f"Invalid YAML: {str(e)}")
    
    def _validate_specification(self, data: Dict[str, Any]) -> None:
        """
        Validate specification structure and content.
        
        Args:
            data: Specification dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(data.keys())
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )
        
        # Validate version
        version = data.get("version")
        if version not in self.SUPPORTED_VERSIONS:
            raise ValidationError(
                f"Unsupported specification version: {version}. "
                f"Supported versions: {', '.join(self.SUPPORTED_VERSIONS)}"
            )
        
        # Validate run_id format
        run_id = data.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("run_"):
            raise ValidationError(
                f"Invalid run_id format: {run_id}. "
                "Expected format: run_YYYY_MM_DD_NNN"
            )
        
        # Validate project_name
        project_name = data.get("project_name")
        if not isinstance(project_name, str) or not project_name.strip():
            raise ValidationError("project_name must be a non-empty string")
        
        # Validate project_description
        project_description = data.get("project_description")
        if not isinstance(project_description, str) or not project_description.strip():
            raise ValidationError("project_description must be a non-empty string")
        
        # Validate scope
        scope = data.get("scope")
        if not isinstance(scope, str) or not scope.strip():
            raise ValidationError("scope must be a non-empty string")
        
        # Validate domains
        domains = data.get("domains")
        if not isinstance(domains, list) or len(domains) == 0:
            raise ValidationError("domains must be a non-empty list")
        
        # Validate dependencies
        dependencies = data.get("dependencies")
        if not isinstance(dependencies, dict):
            raise ValidationError("dependencies must be a dictionary")
        
        # Validate created_at
        created_at = data.get("created_at")
        if not isinstance(created_at, (int, float)):
            raise ValidationError("created_at must be a timestamp (int or float)")
        
        logger.debug("Specification validation passed")
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate a specification dictionary.
        
        Args:
            data: Specification dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self._validate_specification(data)
            return True
        except ValidationError:
            return False
    
    def get_validation_errors(self, data: Dict[str, Any]) -> list[str]:
        """
        Get all validation errors for a specification.
        
        Args:
            data: Specification dictionary
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(data.keys())
        if missing_fields:
            errors.append(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )
        
        # Validate version
        version = data.get("version")
        if version and version not in self.SUPPORTED_VERSIONS:
            errors.append(
                f"Unsupported specification version: {version}"
            )
        
        # Validate run_id format
        run_id = data.get("run_id")
        if run_id and (not isinstance(run_id, str) or not run_id.startswith("run_")):
            errors.append(f"Invalid run_id format: {run_id}")
        
        # Validate project_name
        project_name = data.get("project_name")
        if project_name and (not isinstance(project_name, str) or not project_name.strip()):
            errors.append("project_name must be a non-empty string")
        
        # Validate project_description
        project_description = data.get("project_description")
        if project_description and (not isinstance(project_description, str) or not project_description.strip()):
            errors.append("project_description must be a non-empty string")
        
        # Validate scope
        scope = data.get("scope")
        if scope and (not isinstance(scope, str) or not scope.strip()):
            errors.append("scope must be a non-empty string")
        
        # Validate domains
        domains = data.get("domains")
        if domains and (not isinstance(domains, list) or len(domains) == 0):
            errors.append("domains must be a non-empty list")
        
        # Validate dependencies
        dependencies = data.get("dependencies")
        if dependencies and not isinstance(dependencies, dict):
            errors.append("dependencies must be a dictionary")
        
        # Validate created_at
        created_at = data.get("created_at")
        if created_at and not isinstance(created_at, (int, float)):
            errors.append("created_at must be a timestamp (int or float)")
        
        return errors
