"""Property-based tests for Transition Validation Module.

These tests use Hypothesis to verify correctness properties of the
transition validation system across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from kabbalah.transition_validation import (
    TransitionValidationModule,
    AgentStatus,
    ValidationCheckType,
)


# Strategies for generating test data
agent_ids = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
agent_roles = st.sampled_from([
    "Intake_Clarifier",
    "Root_Planner",
    "Domain_Coordinator",
    "Leaf_Builder",
    "Leaf_Verifier",
    "Leaf_Auditor",
    "Synthesizer_Consolidator"
])
agent_statuses = st.sampled_from([
    AgentStatus.HEALTHY,
    AgentStatus.UNHEALTHY,
    AgentStatus.UNKNOWN,
    AgentStatus.INITIALIZING,
    AgentStatus.DEGRADED
])
error_counts = st.integers(min_value=0, max_value=100)
warning_counts = st.integers(min_value=0, max_value=100)


class TestAgentRegistrationProperties:
    """Property-based tests for agent registration."""
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_registered_agent_is_retrievable(self, agent_id, agent_role):
        """Property: Any registered agent can be retrieved."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        
        agent = module.get_agent_status(agent_id)
        assert agent is not None
        assert agent.agent_id == agent_id
        assert agent.agent_role == agent_role
    
    @given(
        agent_id1=agent_ids,
        agent_id2=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_multiple_agents_all_retrievable(self, agent_id1, agent_id2, agent_role):
        """Property: All registered agents are retrievable."""
        module = TransitionValidationModule()
        
        # Skip if IDs are the same
        if agent_id1 == agent_id2:
            pytest.skip("Agent IDs must be different")
        
        module.register_agent(agent_id1, agent_role)
        module.register_agent(agent_id2, agent_role)
        
        agents = module.get_all_agents_status()
        assert len(agents) == 2
        assert agent_id1 in agents
        assert agent_id2 in agents
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_registered_agent_starts_in_initializing_state(self, agent_id, agent_role):
        """Property: Newly registered agents start in INITIALIZING state."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        
        agent = module.get_agent_status(agent_id)
        assert agent.status == AgentStatus.INITIALIZING


class TestAgentHealthUpdateProperties:
    """Property-based tests for agent health updates."""
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles,
        status=agent_statuses,
        is_responsive=st.booleans(),
        error_count=error_counts
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_health_update_changes_agent_status(
        self,
        agent_id,
        agent_role,
        status,
        is_responsive,
        error_count
    ):
        """Property: Health updates change agent status correctly."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        
        module.update_agent_health(agent_id, status, is_responsive, error_count)
        
        agent = module.get_agent_status(agent_id)
        assert agent.status == status
        assert agent.is_responsive == is_responsive
        assert agent.error_count == error_count
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles,
        error_count=error_counts,
        warning_count=warning_counts
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_health_update_preserves_error_and_warning_counts(
        self,
        agent_id,
        agent_role,
        error_count,
        warning_count
    ):
        """Property: Error and warning counts are preserved in updates."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        
        module.update_agent_health(
            agent_id,
            AgentStatus.HEALTHY,
            True,
            error_count,
            warning_count
        )
        
        agent = module.get_agent_status(agent_id)
        assert agent.error_count == error_count
        assert agent.warning_count == warning_count


class TestAgentHealthValidationProperties:
    """Property-based tests for agent health validation."""
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_healthy_agent_passes_validation(self, agent_id, agent_role):
        """Property: Agents with HEALTHY status and no errors pass validation."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is True
        assert len(unhealthy) == 0
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles,
        status=agent_statuses
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_non_healthy_status_fails_validation(self, agent_id, agent_role, status):
        """Property: Agents with non-HEALTHY status fail validation."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        
        if status != AgentStatus.HEALTHY:
            module.update_agent_health(agent_id, status, True, 0)
            
            all_healthy, unhealthy = module.validate_agent_health()
            assert all_healthy is False
            assert len(unhealthy) == 1
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles,
        error_count=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_agent_with_errors_fails_validation(self, agent_id, agent_role, error_count):
        """Property: Agents with errors fail validation."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, error_count)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is False
        assert len(unhealthy) == 1
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_unresponsive_agent_fails_validation(self, agent_id, agent_role):
        """Property: Unresponsive agents fail validation."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, False, 0)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is False
        assert len(unhealthy) == 1


class TestTransitionValidationProperties:
    """Property-based tests for mode transition validation."""
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_day1_to_day2_with_healthy_agents_succeeds(self, agent_id, agent_role):
        """Property: DAY1→DAY2 transition succeeds when all agents are healthy."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        assert result.is_valid is True
        assert result.all_agents_healthy is True
    
    @given(
        agent_id=agent_ids,
        agent_role=agent_roles,
        status=st.sampled_from([
            AgentStatus.UNHEALTHY,
            AgentStatus.UNKNOWN,
            AgentStatus.INITIALIZING,
            AgentStatus.DEGRADED
        ])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_day1_to_day2_with_unhealthy_agents_fails(self, agent_id, agent_role, status):
        """Property: DAY1→DAY2 transition fails when agents are unhealthy."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, status, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        assert result.is_valid is False
        assert result.all_agents_healthy is False
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_day1_to_day2_without_bootstrap_complete_fails(self, agent_id, agent_role):
        """Property: DAY1→DAY2 transition fails if bootstrap is not complete."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.set_memory_consistency(True)
        # Don't mark bootstrap complete
        
        result = module.validate_transition("DAY1", "DAY2")
        assert result.is_valid is False
        assert result.bootstrap_complete is False
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_day1_to_day2_with_inconsistent_memory_fails(self, agent_id, agent_role):
        """Property: DAY1→DAY2 transition fails if memory is inconsistent."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(False)
        
        result = module.validate_transition("DAY1", "DAY2")
        assert result.is_valid is False
        assert result.memory_consistent is False
    
    @given(
        from_mode=st.sampled_from(["BOOTSTRAP", "DAY1", "DAY2"]),
        to_mode=st.sampled_from(["BOOTSTRAP", "DAY1", "DAY2"])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_non_day1_to_day2_transitions_always_valid(self, from_mode, to_mode):
        """Property: Non-DAY1→DAY2 transitions are always valid."""
        module = TransitionValidationModule()
        
        if from_mode == "DAY1" and to_mode == "DAY2":
            pytest.skip("This is DAY1→DAY2 transition")
        
        result = module.validate_transition(from_mode, to_mode)
        assert result.is_valid is True


class TestValidationHistoryProperties:
    """Property-based tests for validation history."""
    
    @given(
        num_validations=st.integers(min_value=1, max_value=10),
        agent_id=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_validations_recorded_in_history(
        self,
        num_validations,
        agent_id,
        agent_role
    ):
        """Property: All validation attempts are recorded in history."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        for _ in range(num_validations):
            module.validate_transition("DAY1", "DAY2")
        
        history = module.get_validation_history()
        assert len(history) == num_validations
    
    @given(
        num_validations=st.integers(min_value=1, max_value=10),
        agent_id=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_validation_history_is_ordered(
        self,
        num_validations,
        agent_id,
        agent_role
    ):
        """Property: Validation history maintains chronological order."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        for _ in range(num_validations):
            module.validate_transition("DAY1", "DAY2")
        
        history = module.get_validation_history()
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp


class TestResetStateProperties:
    """Property-based tests for state reset."""
    
    @given(
        num_agents=st.integers(min_value=1, max_value=10),
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_reset_clears_all_agents(self, num_agents, agent_role):
        """Property: Reset clears all registered agents."""
        module = TransitionValidationModule()
        
        for i in range(num_agents):
            module.register_agent(f"agent_{i}", agent_role)
        
        assert len(module.get_all_agents_status()) == num_agents
        
        module.reset_validation_state()
        
        assert len(module.get_all_agents_status()) == 0
    
    @given(
        num_validations=st.integers(min_value=1, max_value=10),
        agent_id=agent_ids,
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_reset_clears_validation_history(
        self,
        num_validations,
        agent_id,
        agent_role
    ):
        """Property: Reset clears all validation history."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        for _ in range(num_validations):
            module.validate_transition("DAY1", "DAY2")
        
        assert len(module.get_validation_history()) == num_validations
        
        module.reset_validation_state()
        
        assert len(module.get_validation_history()) == 0


class TestValidationCheckResults:
    """Property-based tests for validation check results."""
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_passed_checks_recorded_correctly(self, agent_id, agent_role):
        """Property: Passed checks are recorded in checks_passed list."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert len(result.checks_passed) == 3
        assert len(result.checks_failed) == 0
        
        check_types = {c.check_type for c in result.checks_passed}
        assert ValidationCheckType.AGENT_HEALTH in check_types
        assert ValidationCheckType.MEMORY_CONSISTENCY in check_types
        assert ValidationCheckType.BOOTSTRAP_COMPLETION in check_types
    
    @given(agent_id=agent_ids, agent_role=agent_roles)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_failed_checks_recorded_correctly(self, agent_id, agent_role):
        """Property: Failed checks are recorded in checks_failed list."""
        module = TransitionValidationModule()
        module.register_agent(agent_id, agent_role)
        module.update_agent_health(agent_id, AgentStatus.UNHEALTHY, False, 1)
        module.set_memory_consistency(False)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert len(result.checks_failed) == 3
        assert len(result.checks_passed) == 0
        
        check_types = {c.check_type for c in result.checks_failed}
        assert ValidationCheckType.AGENT_HEALTH in check_types
        assert ValidationCheckType.MEMORY_CONSISTENCY in check_types
        assert ValidationCheckType.BOOTSTRAP_COMPLETION in check_types


# Validates: Requirements 12.5
class TestDay1ToDay2TransitionValidation:
    """Property-based tests for DAY1 to DAY2 transition validation.
    
    **Validates: Requirements 12.5**
    
    Requirement 12.5: WHEN transitioning from DAY1 to DAY2, THE System SHALL
    validate that all agents are healthy and memory is consistent.
    """
    
    @given(
        num_agents=st.integers(min_value=1, max_value=5),
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_transition_validates_all_agents_healthy(self, num_agents, agent_role):
        """Property: Transition validation checks all agents are healthy."""
        module = TransitionValidationModule()
        
        # Register agents
        for i in range(num_agents):
            module.register_agent(f"agent_{i}", agent_role)
            module.update_agent_health(f"agent_{i}", AgentStatus.HEALTHY, True, 0)
        
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.all_agents_healthy is True
        assert result.is_valid is True
    
    @given(
        num_agents=st.integers(min_value=1, max_value=5),
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_transition_validates_memory_consistency(self, num_agents, agent_role):
        """Property: Transition validation checks memory consistency."""
        module = TransitionValidationModule()
        
        for i in range(num_agents):
            module.register_agent(f"agent_{i}", agent_role)
            module.update_agent_health(f"agent_{i}", AgentStatus.HEALTHY, True, 0)
        
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.memory_consistent is True
        assert result.is_valid is True
    
    @given(
        num_agents=st.integers(min_value=1, max_value=5),
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_transition_fails_if_any_agent_unhealthy(self, num_agents, agent_role):
        """Property: Transition fails if any agent is unhealthy."""
        module = TransitionValidationModule()
        
        for i in range(num_agents):
            module.register_agent(f"agent_{i}", agent_role)
            if i == 0:
                # Make first agent unhealthy
                module.update_agent_health(f"agent_{i}", AgentStatus.UNHEALTHY, False, 1)
            else:
                module.update_agent_health(f"agent_{i}", AgentStatus.HEALTHY, True, 0)
        
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert result.all_agents_healthy is False
    
    @given(
        num_agents=st.integers(min_value=1, max_value=5),
        agent_role=agent_roles
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_transition_fails_if_memory_inconsistent(self, num_agents, agent_role):
        """Property: Transition fails if memory is inconsistent."""
        module = TransitionValidationModule()
        
        for i in range(num_agents):
            module.register_agent(f"agent_{i}", agent_role)
            module.update_agent_health(f"agent_{i}", AgentStatus.HEALTHY, True, 0)
        
        module.mark_bootstrap_complete()
        module.set_memory_consistency(False)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert result.memory_consistent is False
