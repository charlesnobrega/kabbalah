"""Property-based tests for specification parsing.

**Validates: Requirements 1, 13**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime
from kabbalah.intake_node import IntakeNode
from kabbalah.models import UserRequest, Specification


# Strategies for generating test data
project_name_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip() != "")

project_description_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    min_size=1,
    max_size=2000
).filter(lambda x: x.strip() != "")

scope_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != "")
)

constraints_strategy = st.lists(
    st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != ""),
    max_size=10
)

resources_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
    values=st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
    max_size=10
)

metadata_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
    values=st.one_of(st.text(), st.integers()),
    max_size=10
)


class TestSpecificationParsingProperties:
    """Property-based tests for specification parsing."""
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy,
        scope=scope_strategy,
        constraints=constraints_strategy,
        resources=resources_strategy,
        metadata=metadata_strategy
    )
    def test_specification_has_valid_run_id_format(
        self,
        project_name,
        project_description,
        scope,
        constraints,
        resources,
        metadata
    ):
        """Property: All specifications have valid run_id format (run_YYYY_MM_DD_NNN).
        
        **Validates: Requirements 1, 5**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description,
            scope=scope,
            constraints=constraints if constraints else None,
            resources=resources if resources else None,
            metadata=metadata if metadata else None
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Verify run_id format
        import re
        assert re.match(r"^run_\d{4}_\d{2}_\d{2}_\d{3}$", run_id)
        assert spec.run_id == run_id
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_has_all_required_fields(
        self,
        project_name,
        project_description
    ):
        """Property: All specifications have all required fields populated.
        
        **Validates: Requirements 1, 13**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, run_id = intake.parse_request(request)
        
        # Verify all required fields are present and non-empty
        assert spec.run_id
        assert spec.project_name == project_name
        assert spec.project_description == project_description
        assert spec.scope
        assert isinstance(spec.constraints, list)
        assert isinstance(spec.resources, dict)
        assert isinstance(spec.domains, list)
        assert len(spec.domains) > 0
        assert isinstance(spec.dependencies, dict)
        assert spec.created_at > 0
        assert spec.version == "1.0"
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_domains_are_valid(
        self,
        project_name,
        project_description
    ):
        """Property: All domains in specification are valid strings.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify domains
        valid_domains = {"backend", "frontend", "infrastructure", "testing", "documentation"}
        for domain in spec.domains:
            assert isinstance(domain, str)
            assert domain in valid_domains
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_dependencies_are_valid(
        self,
        project_name,
        project_description
    ):
        """Property: All dependencies in specification are valid.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify dependencies
        valid_domains = set(spec.domains)
        for domain, deps in spec.dependencies.items():
            assert domain in valid_domains
            assert isinstance(deps, list)
            for dep in deps:
                assert dep in valid_domains
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_created_at_is_recent(
        self,
        project_name,
        project_description
    ):
        """Property: All specifications have recent created_at timestamp.
        
        **Validates: Requirements 1**
        """
        import time
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        before = time.time()
        spec, _ = intake.parse_request(request)
        after = time.time()
        
        # Verify created_at is within reasonable bounds
        assert before <= spec.created_at <= after
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_scope_is_non_empty(
        self,
        project_name,
        project_description
    ):
        """Property: All specifications have non-empty scope.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify scope
        assert spec.scope
        assert isinstance(spec.scope, str)
        assert len(spec.scope) > 0
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy,
        constraints=constraints_strategy
    )
    def test_specification_preserves_provided_constraints(
        self,
        project_name,
        project_description,
        constraints
    ):
        """Property: Provided constraints are preserved in specification.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description,
            constraints=constraints if constraints else None
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify constraints
        if constraints:
            assert spec.constraints == constraints
        else:
            assert isinstance(spec.constraints, list)
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy,
        resources=resources_strategy
    )
    def test_specification_preserves_provided_resources(
        self,
        project_name,
        project_description,
        resources
    ):
        """Property: Provided resources are preserved in specification.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description,
            resources=resources if resources else None
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify resources
        if resources:
            assert spec.resources == resources
        else:
            assert isinstance(spec.resources, dict)
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy,
        metadata=metadata_strategy
    )
    def test_specification_preserves_provided_metadata(
        self,
        project_name,
        project_description,
        metadata
    ):
        """Property: Provided metadata is preserved in specification.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description,
            metadata=metadata if metadata else None
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify metadata
        if metadata:
            assert spec.metadata == metadata
        else:
            assert isinstance(spec.metadata, dict)
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_run_id_uniqueness(
        self,
        project_name,
        project_description
    ):
        """Property: Consecutive specifications have unique run_ids.
        
        **Validates: Requirements 1, 5**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec1, run_id1 = intake.parse_request(request)
        spec2, run_id2 = intake.parse_request(request)
        
        # Verify uniqueness
        assert run_id1 != run_id2
        assert spec1.run_id != spec2.run_id
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_backend_always_present(
        self,
        project_name,
        project_description
    ):
        """Property: Backend domain is always present in specifications.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify backend is always present
        assert "backend" in spec.domains
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_frontend_always_present(
        self,
        project_name,
        project_description
    ):
        """Property: Frontend domain is always present in specifications.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify frontend is always present
        assert "frontend" in spec.domains
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_frontend_depends_on_backend(
        self,
        project_name,
        project_description
    ):
        """Property: Frontend always depends on backend.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify frontend depends on backend
        assert "backend" in spec.dependencies.get("frontend", [])
    
    @given(
        project_name=project_name_strategy,
        project_description=project_description_strategy
    )
    def test_specification_backend_has_no_dependencies(
        self,
        project_name,
        project_description
    ):
        """Property: Backend domain has no dependencies.
        
        **Validates: Requirements 1**
        """
        intake = IntakeNode()
        request = UserRequest(
            project_name=project_name,
            project_description=project_description
        )
        
        spec, _ = intake.parse_request(request)
        
        # Verify backend has no dependencies
        assert spec.dependencies.get("backend", []) == []
