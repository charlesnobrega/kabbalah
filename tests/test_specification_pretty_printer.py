"""
Tests for Specification Pretty Printer
"""

import pytest
import json
import time
from src.kabbalah.specification_pretty_printer import (
    SpecificationPrettyPrinter,
    OutputFormat,
    FormattingError,
)


class TestSpecificationPrettyPrinter:
    """Test Specification Pretty Printer"""
    
    def test_printer_initialization(self):
        """Test printer initialization"""
        printer = SpecificationPrettyPrinter()
        assert printer is not None
        assert printer.indent == 2
    
    def test_printer_initialization_custom_indent(self):
        """Test printer initialization with custom indent"""
        printer = SpecificationPrettyPrinter(indent=4)
        assert printer.indent == 4
    
    def test_format_json(self):
        """Test formatting as JSON"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_json(spec)
        
        assert isinstance(result, str)
        assert "run_id" in result
        assert "Test Project" in result
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["project_name"] == "Test Project"
    
    def test_format_json_with_indent(self):
        """Test JSON formatting respects indent"""
        printer = SpecificationPrettyPrinter(indent=4)
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_json(spec)
        
        # Check for 4-space indentation
        assert "    " in result
    
    def test_format_text(self):
        """Test formatting as text"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend", "frontend"],
            "dependencies": {"frontend": ["backend"]},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_text(spec)
        
        assert isinstance(result, str)
        assert "SPECIFICATION" in result
        assert "Test Project" in result
        assert "backend" in result
        assert "frontend" in result
    
    def test_format_text_contains_sections(self):
        """Test text formatting contains all sections"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_text(spec)
        
        assert "BASIC INFORMATION" in result
        assert "SCOPE" in result
        assert "DOMAINS" in result
        assert "CONSTRAINTS" in result
        assert "RESOURCES" in result
        assert "DEPENDENCIES" in result
        assert "METADATA" in result
        assert "TIMESTAMPS" in result
    
    def test_format_text_with_constraints(self):
        """Test text formatting with constraints"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
            "constraints": ["Constraint 1", "Constraint 2"],
        }
        
        result = printer.format_text(spec)
        
        assert "Constraint 1" in result
        assert "Constraint 2" in result
    
    def test_format_text_with_resources(self):
        """Test text formatting with resources"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
            "resources": {"cpu": 4, "memory": 8},
        }
        
        result = printer.format_text(spec)
        
        assert "cpu: 4" in result
        assert "memory: 8" in result
    
    def test_format_text_with_metadata(self):
        """Test text formatting with metadata"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
            "metadata": {"client": "Acme Corp"},
        }
        
        result = printer.format_text(spec)
        
        assert "client: Acme Corp" in result
    
    def test_pretty_print_json(self):
        """Test pretty_print with JSON format"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.pretty_print(spec, OutputFormat.JSON)
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["project_name"] == "Test Project"
    
    def test_pretty_print_text(self):
        """Test pretty_print with TEXT format"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.pretty_print(spec, OutputFormat.TEXT)
        
        assert "SPECIFICATION" in result
        assert "Test Project" in result
    
    def test_pretty_print_unsupported_format(self):
        """Test pretty_print with unsupported format"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        with pytest.raises(FormattingError):
            printer.pretty_print(spec, "unsupported")
    
    def test_format_text_wrapping(self):
        """Test text wrapping in text format"""
        printer = SpecificationPrettyPrinter()
        long_scope = "This is a very long scope description that should be wrapped to multiple lines when formatted as text to ensure readability and proper formatting"
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": long_scope,
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_text(spec)
        
        # Should contain the scope text
        assert "very long scope" in result
    
    def test_format_text_with_complex_dependencies(self):
        """Test text formatting with complex dependencies"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend", "frontend", "infrastructure"],
            "dependencies": {
                "frontend": ["backend"],
                "infrastructure": ["backend"],
            },
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_text(spec)
        
        assert "frontend:" in result
        assert "infrastructure:" in result
        assert "backend" in result
    
    def test_format_json_with_special_characters(self):
        """Test JSON formatting with special characters"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project™",
            "project_description": "A test project with special chars: é, ñ, ü",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        result = printer.format_json(spec)
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert "™" in parsed["project_name"]
    
    def test_format_text_with_empty_optional_fields(self):
        """Test text formatting with empty optional fields"""
        printer = SpecificationPrettyPrinter()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": 1234567890.0,
            "version": "1.0",
            "constraints": [],
            "resources": {},
            "metadata": {},
        }
        
        result = printer.format_text(spec)
        
        assert "(No constraints specified)" in result
        assert "(No resources specified)" in result
        assert "(No metadata)" in result
    
    def test_round_trip_json(self):
        """Test round-trip: format to JSON and parse back"""
        printer = SpecificationPrettyPrinter()
        original_spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend", "frontend"],
            "dependencies": {"frontend": ["backend"]},
            "created_at": 1234567890.0,
            "version": "1.0",
        }
        
        # Format to JSON
        json_str = printer.format_json(original_spec)
        
        # Parse back
        parsed_spec = json.loads(json_str)
        
        # Should match original
        assert parsed_spec == original_spec


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
