"""Property-based tests for MemoryGovernanceModule."""

import tempfile
from hypothesis import given, strategies as st, assume

from kabbalah.memory_governance import (
    MemoryGovernanceModule,
    MemoryCategory,
    MemoryOperation,
    CANONICAL_ROLES,
)


# Strategies for property-based testing
canonical_roles_strategy = st.sampled_from(list(CANONICAL_ROLES))
memory_categories_strategy = st.sampled_from(
    [MemoryCategory.SHARED.value, MemoryCategory.DOMAIN_SPECIFIC.value, MemoryCategory.ROLE_SPECIFIC.value]
)
operations_strategy = st.sampled_from([MemoryOperation.READ.value, MemoryOperation.WRITE.value])
trace_ids_strategy = st.text(min_size=1, max_size=100)


class TestAccessControlEnforcement:
    """Property tests for access control enforcement."""

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_access_check_returns_boolean(self, agent_role, memory_category, operation):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: check_memory_access always returns a boolean value.
        """
        module = MemoryGovernanceModule()
        result = module.check_memory_access(agent_role, memory_category, operation)
        assert isinstance(result, bool)

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_shared_memory_always_accessible(self, agent_role, memory_category, operation):
        """
        **Validates: Requirements 15.1, 15.3**
        
        Property: Shared memory is always accessible to all roles.
        """
        module = MemoryGovernanceModule()
        
        if memory_category == MemoryCategory.SHARED.value:
            result = module.check_memory_access(agent_role, memory_category, operation)
            assert result is True

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_domain_specific_access_consistency(self, agent_role, memory_category, operation):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: Domain-specific access decisions are consistent across multiple calls.
        """
        module = MemoryGovernanceModule()
        
        result1 = module.check_memory_access(agent_role, memory_category, operation)
        result2 = module.check_memory_access(agent_role, memory_category, operation)
        
        assert result1 == result2

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_access_logging_does_not_affect_access_check(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.1, 15.4**
        
        Property: Logging access does not change the access control decision.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            # Check access before logging
            result_before = module.check_memory_access(agent_role, memory_category, operation)
            
            # Log the access
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            # Check access after logging
            result_after = module.check_memory_access(agent_role, memory_category, operation)
            
            assert result_before == result_after

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_access_log_reflects_access_decision(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Access logs accurately reflect the access control decision.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            # Check access
            allowed = module.check_memory_access(agent_role, memory_category, operation)
            
            # Log the access
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            # Retrieve logs
            logs = module.get_access_logs(agent_role=agent_role, trace_id=trace_id)
            
            assert len(logs) > 0
            assert logs[-1].allowed == allowed

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_access_log_contains_all_required_fields(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Access logs contain all required fields.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            logs = module.get_access_logs(limit=1)
            assert len(logs) > 0
            
            log = logs[-1]
            assert log.access_id is not None
            assert log.agent_role == agent_role
            assert log.memory_category == memory_category
            assert log.operation == operation
            assert log.trace_id == trace_id
            assert log.allowed is not None
            assert log.timestamp > 0

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_domain_specific_access_rules(self, agent_role, memory_category, operation):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: Domain-specific memory access follows defined rules.
        """
        module = MemoryGovernanceModule()
        
        if memory_category == MemoryCategory.DOMAIN_SPECIFIC.value:
            result = module.check_memory_access(agent_role, memory_category, operation)
            
            # Only domain roles should have access
            domain_roles = {
                "Domain_Coordinator",
                "Leaf_Builder",
                "Leaf_Verifier",
                "Leaf_Auditor",
            }
            
            if agent_role in domain_roles:
                assert result is True
            else:
                assert result is False


class TestAccessLogging:
    """Property tests for access logging."""

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_each_log_has_unique_access_id(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Each access log has a unique access_id.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            # Log multiple accesses
            for i in range(5):
                module.log_memory_access(
                    agent_role, memory_category, operation, f"{trace_id}_{i}"
                )
            
            logs = module.get_access_logs(limit=10)
            access_ids = [log.access_id for log in logs]
            
            # All access_ids should be unique
            assert len(access_ids) == len(set(access_ids))

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_logs_are_retrievable_by_trace_id(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Logged accesses can be retrieved by trace_id.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            logs = module.get_access_logs(trace_id=trace_id)
            
            assert len(logs) > 0
            assert all(log.trace_id == trace_id for log in logs)

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_logs_are_retrievable_by_agent_role(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Logged accesses can be retrieved by agent_role.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            logs = module.get_access_logs(agent_role=agent_role)
            
            assert len(logs) > 0
            assert all(log.agent_role == agent_role for log in logs)

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_logs_are_retrievable_by_memory_category(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Logged accesses can be retrieved by memory_category.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            module.log_memory_access(agent_role, memory_category, operation, trace_id)
            
            logs = module.get_access_logs(memory_category=memory_category)
            
            assert len(logs) > 0
            assert all(log.memory_category == memory_category for log in logs)

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_log_limit_is_respected(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: get_access_logs respects the limit parameter.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            # Log 20 accesses
            for i in range(20):
                module.log_memory_access(
                    agent_role, memory_category, operation, f"{trace_id}_{i}"
                )
            
            for limit in [1, 5, 10, 15]:
                logs = module.get_access_logs(limit=limit)
                assert len(logs) <= limit

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
        trace_id=trace_ids_strategy,
    )
    def test_logs_preserve_metadata(
        self, agent_role, memory_category, operation, trace_id
    ):
        """
        **Validates: Requirements 15.4, 15.5**
        
        Property: Access logs preserve optional metadata.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            metadata = {"key1": "value1", "key2": "value2"}
            module.log_memory_access(
                agent_role, memory_category, operation, trace_id, metadata=metadata
            )
            
            logs = module.get_access_logs(trace_id=trace_id)
            assert len(logs) > 0
            assert logs[-1].metadata == metadata


class TestAccessControlConsistency:
    """Property tests for access control consistency."""

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_access_decision_is_deterministic(
        self, agent_role, memory_category, operation
    ):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: Access control decisions are deterministic.
        """
        module = MemoryGovernanceModule()
        
        results = [
            module.check_memory_access(agent_role, memory_category, operation)
            for _ in range(10)
        ]
        
        # All results should be the same
        assert len(set(results)) == 1

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_access_decision_independent_of_module_state(
        self, agent_role, memory_category, operation
    ):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: Access decisions are independent of module state.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            module = MemoryGovernanceModule(audit_log_path=tmpdir)
            
            # Check access before any logging
            result_before = module.check_memory_access(agent_role, memory_category, operation)
            
            # Log many accesses
            for i in range(100):
                module.log_memory_access(
                    agent_role, memory_category, operation, f"trace_{i}"
                )
            
            # Check access after logging
            result_after = module.check_memory_access(agent_role, memory_category, operation)
            
            assert result_before == result_after

    @given(
        agent_role=canonical_roles_strategy,
        memory_category=memory_categories_strategy,
        operation=operations_strategy,
    )
    def test_access_decision_independent_of_module_instance(
        self, agent_role, memory_category, operation
    ):
        """
        **Validates: Requirements 15.1, 15.2**
        
        Property: Access decisions are consistent across module instances.
        """
        module1 = MemoryGovernanceModule()
        module2 = MemoryGovernanceModule()
        
        result1 = module1.check_memory_access(agent_role, memory_category, operation)
        result2 = module2.check_memory_access(agent_role, memory_category, operation)
        
        assert result1 == result2
