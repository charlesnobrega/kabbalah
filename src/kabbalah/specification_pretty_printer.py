"""
Specification Pretty Printer

Formats specifications for human-readable output in JSON/YAML formats.
"""

import json
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats"""
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"


class FormattingError(Exception):
    """Raised when specification formatting fails"""
    pass


class SpecificationPrettyPrinter:
    """
    Formats specifications for human-readable output.
    
    Features:
    - JSON formatting with indentation
    - YAML formatting
    - Text formatting with sections
    - Customizable indentation
    - Comprehensive error handling
    """
    
    def __init__(self, indent: int = 2):
        """
        Initialize the pretty printer.
        
        Args:
            indent: Number of spaces for indentation (default: 2)
        """
        self.indent = indent
    
    def pretty_print(
        self,
        specification: Dict[str, Any],
        format: OutputFormat = OutputFormat.JSON,
    ) -> str:
        """
        Format a specification for output.
        
        Args:
            specification: Specification dictionary
            format: Output format (JSON, YAML, or TEXT)
            
        Returns:
            Formatted specification string
        """
        try:
            if format == OutputFormat.JSON:
                return self._format_json(specification)
            elif format == OutputFormat.YAML:
                return self._format_yaml(specification)
            elif format == OutputFormat.TEXT:
                return self._format_text(specification)
            else:
                raise FormattingError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Formatting failed: {str(e)}")
            raise FormattingError(f"Failed to format specification: {str(e)}")
    
    def _format_json(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as JSON.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            JSON formatted string
        """
        return json.dumps(specification, indent=self.indent, default=str)
    
    def _format_yaml(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as YAML.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            YAML formatted string
        """
        try:
            import yaml
            
            # Custom representer for better formatting
            def represent_none(self, _):
                return self.represent_scalar('tag:yaml.org,2002:null', '')
            
            yaml.add_representer(type(None), represent_none)
            
            return yaml.dump(
                specification,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        except ImportError:
            raise FormattingError("YAML support requires PyYAML to be installed")
        except Exception as e:
            raise FormattingError(f"YAML formatting failed: {str(e)}")
    
    def _format_text(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as human-readable text.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            Text formatted string
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("SPECIFICATION")
        lines.append("=" * 80)
        lines.append("")
        
        # Basic information
        lines.append("BASIC INFORMATION")
        lines.append("-" * 80)
        lines.append(f"Run ID:              {specification.get('run_id', 'N/A')}")
        lines.append(f"Version:             {specification.get('version', 'N/A')}")
        lines.append(f"Project Name:        {specification.get('project_name', 'N/A')}")
        lines.append(f"Project Description: {specification.get('project_description', 'N/A')}")
        lines.append("")
        
        # Scope
        lines.append("SCOPE")
        lines.append("-" * 80)
        scope = specification.get('scope', 'N/A')
        lines.append(self._wrap_text(scope, 80))
        lines.append("")
        
        # Domains
        lines.append("DOMAINS")
        lines.append("-" * 80)
        domains = specification.get('domains', [])
        for domain in domains:
            lines.append(f"  • {domain}")
        lines.append("")
        
        # Constraints
        lines.append("CONSTRAINTS")
        lines.append("-" * 80)
        constraints = specification.get('constraints', [])
        if constraints:
            for constraint in constraints:
                lines.append(f"  • {constraint}")
        else:
            lines.append("  (No constraints specified)")
        lines.append("")
        
        # Resources
        lines.append("RESOURCES")
        lines.append("-" * 80)
        resources = specification.get('resources', {})
        if resources:
            for key, value in resources.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (No resources specified)")
        lines.append("")
        
        # Dependencies
        lines.append("DEPENDENCIES")
        lines.append("-" * 80)
        dependencies = specification.get('dependencies', {})
        if dependencies:
            for domain, deps in dependencies.items():
                if deps:
                    lines.append(f"  {domain}:")
                    for dep in deps:
                        lines.append(f"    → {dep}")
                else:
                    lines.append(f"  {domain}: (no dependencies)")
        else:
            lines.append("  (No dependencies specified)")
        lines.append("")
        
        # Metadata
        lines.append("METADATA")
        lines.append("-" * 80)
        metadata = specification.get('metadata', {})
        if metadata:
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (No metadata)")
        lines.append("")
        
        # Timestamps
        lines.append("TIMESTAMPS")
        lines.append("-" * 80)
        created_at = specification.get('created_at', 'N/A')
        lines.append(f"Created At: {created_at}")
        lines.append("")
        
        # Footer
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _wrap_text(self, text: str, width: int) -> str:
        """
        Wrap text to specified width.
        
        Args:
            text: Text to wrap
            width: Maximum line width
            
        Returns:
            Wrapped text
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def format_json(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as JSON.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            JSON formatted string
        """
        return self.pretty_print(specification, OutputFormat.JSON)
    
    def format_yaml(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as YAML.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            YAML formatted string
        """
        return self.pretty_print(specification, OutputFormat.YAML)
    
    def format_text(self, specification: Dict[str, Any]) -> str:
        """
        Format specification as text.
        
        Args:
            specification: Specification dictionary
            
        Returns:
            Text formatted string
        """
        return self.pretty_print(specification, OutputFormat.TEXT)
