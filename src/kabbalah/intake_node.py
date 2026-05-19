"""Intake Node - Parses user requests and generates premium specifications."""

import re
import time
from datetime import datetime
from typing import Tuple
from kabbalah.models import UserRequest, Specification


class InvalidRequestError(Exception):
    """Raised when a user request is invalid."""
    pass


class SpecificationError(Exception):
    """Raised when specification generation fails."""
    pass


class IntakeNode:
    """
    Intake Node component of Kabbalah orchestration system.
    
    Responsibility: Parse user requests and generate premium project specifications.
    
    Contracts:
    - Pre-condition: request is non-null and contains required fields
    - Post-condition: specification is valid and run_id is unique
    - Invariant: run_id format matches pattern "run_YYYY_MM_DD_NNN"
    """
    
    # Counter for generating unique run_ids within a day
    _run_counter = 0
    _last_date = None
    
    def parse_request(self, request: UserRequest) -> Tuple[Specification, str]:
        """
        Parse user request into premium specification.
        
        Args:
            request: User's project request
            
        Returns:
            (specification, run_id)
            
        Raises:
            InvalidRequestError: If request is malformed
            SpecificationError: If specification cannot be generated
        """
        # Validate pre-conditions
        self._validate_request(request)
        
        # Generate run_id
        run_id = self._generate_run_id()
        
        # Generate specification
        specification = self._generate_specification(request, run_id)
        
        # Validate post-conditions
        self._validate_specification(specification, run_id)
        
        return specification, run_id
    
    def _validate_request(self, request: UserRequest) -> None:
        """
        Validate that request is non-null and contains required fields.
        
        Args:
            request: User request to validate
            
        Raises:
            InvalidRequestError: If request is invalid
        """
        if request is None:
            raise InvalidRequestError("Request cannot be null")
        
        if not request.project_name or not isinstance(request.project_name, str):
            raise InvalidRequestError("project_name is required and must be a string")
        
        if not request.project_description or not isinstance(request.project_description, str):
            raise InvalidRequestError("project_description is required and must be a string")
        
        if request.project_name.strip() == "":
            raise InvalidRequestError("project_name cannot be empty")
        
        if request.project_description.strip() == "":
            raise InvalidRequestError("project_description cannot be empty")
    
    def _generate_run_id(self) -> str:
        """
        Generate a unique run_id with format "run_YYYY_MM_DD_NNN".
        
        Returns:
            Unique run_id string
        """
        now = datetime.utcnow()
        date_str = now.strftime("%Y_%m_%d")
        
        # Reset counter if date changed
        if date_str != IntakeNode._last_date:
            IntakeNode._last_date = date_str
            IntakeNode._run_counter = 0
        
        # Increment counter
        IntakeNode._run_counter += 1
        
        # Cap counter at 999 to maintain format
        if IntakeNode._run_counter > 999:
            IntakeNode._run_counter = 1
        
        counter_str = str(IntakeNode._run_counter).zfill(3)
        
        run_id = f"run_{date_str}_{counter_str}"
        return run_id
    
    def _generate_specification(self, request: UserRequest, run_id: str) -> Specification:
        """
        Generate a premium project specification from the request.
        
        Args:
            request: User request
            run_id: Unique execution identifier
            
        Returns:
            Premium project specification
            
        Raises:
            SpecificationError: If specification generation fails
        """
        try:
            # Preserve explicit empty values, only infer if None
            if request.scope is None:
                scope = self._infer_scope(request.project_description)
            else:
                scope = request.scope
            
            # Preserve explicit empty lists, only generate defaults if None
            if request.constraints is None:
                constraints = self._generate_default_constraints()
            else:
                constraints = request.constraints
            
            # Preserve explicit empty dicts, only generate defaults if None
            if request.resources is None:
                resources = self._generate_default_resources()
            else:
                resources = request.resources
            
            # Ensure scope is not empty after inference
            if not scope or not scope.strip():
                scope = "general"
            
            # Infer domains from scope and description
            domains = self._infer_domains(scope, request.project_description)
            
            # Infer dependencies between domains
            dependencies = self._infer_dependencies(domains)
            
            specification = Specification(
                run_id=run_id,
                project_name=request.project_name,
                project_description=request.project_description,
                scope=scope,
                constraints=constraints,
                resources=resources,
                domains=domains,
                dependencies=dependencies,
                metadata=request.metadata or {},
                created_at=time.time(),
                version="1.0"
            )
            
            return specification
        except Exception as e:
            raise SpecificationError(f"Failed to generate specification: {str(e)}")
    
    def _infer_scope(self, description: str) -> str:
        """
        Infer project scope from description.
        
        Args:
            description: Project description
            
        Returns:
            Inferred scope
        """
        # Simple heuristic: use first 200 characters or first sentence
        sentences = description.split(".")
        if sentences:
            scope = sentences[0].strip()
            if len(scope) > 200:
                scope = scope[:200] + "..."
            return scope
        return description[:200]
    
    def _generate_default_constraints(self) -> list:
        """Generate default constraints."""
        return [
            "Must follow best practices",
            "Must include error handling",
            "Must be maintainable"
        ]
    
    def _generate_default_resources(self) -> dict:
        """Generate default resources."""
        return {
            "max_tokens": 4000,
            "timeout_seconds": 300,
            "retry_count": 3
        }
    
    def _infer_domains(self, scope: str, description: str) -> list:
        """
        Infer domains from scope and description.
        
        Args:
            scope: Project scope
            description: Project description
            
        Returns:
            List of inferred domains
        """
        # Default domains for any project
        domains = ["backend", "frontend"]
        
        # Add infrastructure if mentioned
        if any(word in description.lower() for word in ["deploy", "infrastructure", "cloud", "aws", "docker"]):
            domains.append("infrastructure")
        
        # Add testing if mentioned
        if any(word in description.lower() for word in ["test", "testing", "qa"]):
            domains.append("testing")
        
        # Add documentation if mentioned
        if any(word in description.lower() for word in ["document", "documentation", "api doc"]):
            domains.append("documentation")
        
        return domains
    
    def _infer_dependencies(self, domains: list) -> dict:
        """
        Infer dependencies between domains.
        
        Args:
            domains: List of domains
            
        Returns:
            Dictionary mapping domain to list of dependent domains
        """
        dependencies = {}
        
        for domain in domains:
            dependencies[domain] = []
        
        # Frontend depends on backend
        if "frontend" in domains and "backend" in domains:
            dependencies["frontend"].append("backend")
        
        # Testing depends on backend and frontend
        if "testing" in domains:
            if "backend" in domains:
                dependencies["testing"].append("backend")
            if "frontend" in domains:
                dependencies["testing"].append("frontend")
        
        # Infrastructure can depend on backend
        if "infrastructure" in domains and "backend" in domains:
            dependencies["infrastructure"].append("backend")
        
        return dependencies
    
    def _validate_specification(self, specification: Specification, run_id: str) -> None:
        """
        Validate that specification is valid and run_id is unique.
        
        Args:
            specification: Specification to validate
            run_id: Run ID to validate
            
        Raises:
            SpecificationError: If specification or run_id is invalid
        """
        # Validate run_id format
        run_id_pattern = r"^run_\d{4}_\d{2}_\d{2}_\d{3}$"
        if not re.match(run_id_pattern, run_id):
            raise SpecificationError(f"Invalid run_id format: {run_id}")
        
        # Validate specification has required fields
        if not specification.project_name:
            raise SpecificationError("Specification must have project_name")
        
        if not specification.project_description:
            raise SpecificationError("Specification must have project_description")
        
        if not specification.scope:
            raise SpecificationError("Specification must have scope")
        
        if not specification.domains:
            raise SpecificationError("Specification must have at least one domain")
        
        if specification.run_id != run_id:
            raise SpecificationError("Specification run_id does not match provided run_id")
