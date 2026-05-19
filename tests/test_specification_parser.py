"""
Tests for Specification Parser
"""

import pytest
import json
import time
from src.kabbalah.specification_parser import (
    SpecificationParser,
    SpecificationFormat,
    ParsingError,
    ValidationError,
    ParseResult,
)


class TestSpecificationParser:
    """Test Specification Parser"""
    
    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = SpecificationParser()
        assert parser is not None
        assert parser.last_parsed_format is None
        assert parser.last_parsed_version is None
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON specification"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend", "frontend"],
            "dependencies": {"frontend": ["backend"]},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        json_str = json.dumps(spec)
        result = parser.parse(json_str, SpecificationFormat.JSON)
        
        assert result.success
        assert result.data == spec
        assert result.format == SpecificationFormat.JSON
        assert result.version == "1.0"
    
    def test_parse_dict_directly(self):
        """Test parsing dictionary directly"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert result.success
        assert result.data == spec
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        parser = SpecificationParser()
        invalid_json = "{invalid json}"
        
        result = parser.parse(invalid_json, SpecificationFormat.JSON)
        
        assert not result.success
        assert result.error is not None
        assert "Invalid JSON" in result.error
    
    def test_parse_missing_required_fields(self):
        """Test parsing with missing required fields"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            # Missing project_description
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "Missing required fields" in result.error
    
    def test_parse_invalid_run_id_format(self):
        """Test parsing with invalid run_id format"""
        parser = SpecificationParser()
        spec = {
            "run_id": "invalid_format",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "Invalid run_id format" in result.error
    
    def test_parse_empty_project_name(self):
        """Test parsing with empty project_name"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "project_name must be a non-empty string" in result.error
    
    def test_parse_empty_domains(self):
        """Test parsing with empty domains"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": [],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "domains must be a non-empty list" in result.error
    
    def test_parse_unsupported_version(self):
        """Test parsing with unsupported version"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "2.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "Unsupported specification version" in result.error
    
    def test_validate_valid_specification(self):
        """Test validating a valid specification"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        assert parser.validate(spec)
    
    def test_validate_invalid_specification(self):
        """Test validating an invalid specification"""
        parser = SpecificationParser()
        spec = {
            "run_id": "invalid",
            "project_name": "",
        }
        
        assert not parser.validate(spec)
    
    def test_get_validation_errors(self):
        """Test getting validation errors"""
        parser = SpecificationParser()
        spec = {
            "run_id": "invalid",
            "project_name": "",
        }
        
        errors = parser.get_validation_errors(spec)
        
        assert len(errors) > 0
        assert any("Missing required fields" in e for e in errors)
    
    def test_parse_with_metadata(self):
        """Test parsing specification with metadata"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
            "metadata": {"key": "value"},
        }
        
        result = parser.parse(spec)
        
        assert result.success
        assert result.data["metadata"]["key"] == "value"
    
    def test_parse_with_constraints(self):
        """Test parsing specification with constraints"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
            "constraints": ["Constraint 1", "Constraint 2"],
        }
        
        result = parser.parse(spec)
        
        assert result.success
        assert len(result.data["constraints"]) == 2
    
    def test_parse_with_resources(self):
        """Test parsing specification with resources"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
            "resources": {"cpu": 4, "memory": 8},
        }
        
        result = parser.parse(spec)
        
        assert result.success
        assert result.data["resources"]["cpu"] == 4
    
    def test_parse_stores_metadata(self):
        """Test that parser stores metadata after parsing"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert parser.last_parsed_format == SpecificationFormat.JSON
        assert parser.last_parsed_version == "1.0"
    
    def test_parse_auto_detect_json(self):
        """Test auto-detection of JSON format"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": time.time(),
            "version": "1.0",
        }
        
        json_str = json.dumps(spec)
        result = parser.parse(json_str)  # No format specified
        
        assert result.success
        assert result.format == SpecificationFormat.JSON
    
    def test_parse_invalid_created_at(self):
        """Test parsing with invalid created_at"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": {},
            "created_at": "not a timestamp",
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "created_at must be a timestamp" in result.error
    
    def test_parse_invalid_dependencies_type(self):
        """Test parsing with invalid dependencies type"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "Test Project",
            "project_description": "A test project",
            "scope": "Test scope",
            "domains": ["backend"],
            "dependencies": ["not", "a", "dict"],
            "created_at": time.time(),
            "version": "1.0",
        }
        
        result = parser.parse(spec)
        
        assert not result.success
        assert "dependencies must be a dictionary" in result.error
    
    def test_parse_complex_specification(self):
        """Test parsing a complex specification"""
        parser = SpecificationParser()
        spec = {
            "run_id": "run_2026_04_11_001",
            "project_name": "E-Commerce Platform",
            "project_description": "Build a scalable e-commerce platform",
            "scope": "Full-stack web application",
            "domains": ["backend", "frontend", "infrastructure", "testing"],
            "dependencies": {
                "frontend": ["backend"],
                "testing": ["backend", "frontend"],
                "infrastructure": ["backend"],
            },
            "created_at": time.time(),
            "version": "1.0",
            "constraints": [
                "Must support 10k concurrent users",
                "Must have 99.9% uptime",
            ],
            "resources": {
                "budget": 50000,
                "team_size": 5,
                "timeline_weeks": 12,
            },
            "metadata": {
                "client": "Acme Corp",
                "deadline": "2026-06-30",
            },
        }
        
        result = parser.parse(spec)
        
        assert result.success
        assert len(result.data["domains"]) == 4
        assert len(result.data["constraints"]) == 2
        assert result.data["resources"]["budget"] == 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
