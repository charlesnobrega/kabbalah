"""Unit tests for Transition Validation Module."""

import pytest
import time
from kabbalah.transition_validation import (
    TransitionValidationModule,
    AgentStatus,
    ValidationCheckType,
    AgentHealthStatus,
    ValidationCheckResult,
    TransitionValidationResult,
)


class TestTransitionValidationModuleInitialization:
    """Test initialization of TransitionValidationModule."""
    
    def test_initialization_creates_empty_agent_registry(self):
        """Test that initialization creates empty agent registry."""
        module = TransitionValidationModule()
        assert module.get_all_agents_status() == {}
    
    def test_initialization_creates_empty_validation_history(self):
        """Test that initialization creates empty validation history."""
        module = TransitionValidationModule()
        assert module.get_validation_history() == []
    
    def test_initialization_bootstrap_not_complete(self):
        """Test that bootstrap is not marked complete on initialization."""
        module = TransitionValidationModule()
        _, bootstrap_details = module.validate_bootstrap_completion()
        assert "pending" in bootstrap_details.lower()
    
    def test_initialization_memory_consistent(self):
        """Test that memory is marked consistent on initialization."""
        module = TransitionValidationModule()
        is_consistent, _ = module.validate_memory_consistency()
        assert is_consistent is True


class TestAgentRegistration:
    """Test agent registration functionality."""
    
    def test_register_agent_success(self):
        """Test successful agent registration."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        agent = module.get_agent_status("agent_1")
        assert agent is not None
        assert agent.agent_id == "agent_1"
        assert agent.agent_role == "Leaf_Builder"
        assert agent.status == AgentStatus.INITIALIZING
    
    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.register_agent("agent_2", "Leaf_Verifier")
        module.register_agent("agent_3", "Leaf_Auditor")
        
        agents = module.get_all_agents_status()
        assert len(agents) == 3
        assert "agent_1" in agents
        assert "agent_2" in agents
        assert "agent_3" in agents
    
    def test_register_agent_with_metadata(self):
        """Test registering agent with metadata."""
        module = TransitionValidationModule()
        metadata = {"version": "1.0", "provider": "openai"}
        module.register_agent("agent_1", "Leaf_Builder", metadata=metadata)
        
        agent = module.get_agent_status("agent_1")
        assert agent.metadata == metadata
    
    def test_register_agent_empty_id_raises_error(self):
        """Test that registering agent with empty ID raises error."""
        module = TransitionValidationModule()
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            module.register_agent("", "Leaf_Builder")
    
    def test_register_agent_empty_role_raises_error(self):
        """Test that registering agent with empty role raises error."""
        module = TransitionValidationModule()
        with pytest.raises(ValueError, match="agent_role cannot be empty"):
            module.register_agent("agent_1", "")
    
    def test_register_agent_overwrites_existing(self):
        """Test that registering agent with same ID overwrites."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.register_agent("agent_1", "Leaf_Verifier")
        
        agent = module.get_agent_status("agent_1")
        assert agent.agent_role == "Leaf_Verifier"


class TestAgentHealthUpdate:
    """Test agent health update functionality."""
    
    def test_update_agent_health_success(self):
        """Test successful agent health update."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        module.update_agent_health(
            "agent_1",
            AgentStatus.HEALTHY,
            is_responsive=True,
            error_count=0
        )
        
        agent = module.get_agent_status("agent_1")
        assert agent.status == AgentStatus.HEALTHY
        assert agent.is_responsive is True
        assert agent.error_count == 0
    
    def test_update_agent_health_with_errors(self):
        """Test updating agent health with errors."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        module.update_agent_health(
            "agent_1",
            AgentStatus.UNHEALTHY,
            is_responsive=False,
            error_count=5,
            warning_count=2
        )
        
        agent = module.get_agent_status("agent_1")
        assert agent.status == AgentStatus.UNHEALTHY
        assert agent.is_responsive is False
        assert agent.error_count == 5
        assert agent.warning_count == 2
    
    def test_update_agent_health_unregistered_raises_error(self):
        """Test that updating unregistered agent raises error."""
        module = TransitionValidationModule()
        with pytest.raises(ValueError, match="not registered"):
            module.update_agent_health(
                "agent_1",
                AgentStatus.HEALTHY,
                is_responsive=True
            )
    
    def test_update_agent_health_updates_heartbeat(self):
        """Test that updating health updates heartbeat."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        initial_heartbeat = module.get_agent_status("agent_1").last_heartbeat
        time.sleep(0.01)  # Small delay
        
        module.update_agent_health(
            "agent_1",
            AgentStatus.HEALTHY,
            is_responsive=True
        )
        
        updated_heartbeat = module.get_agent_status("agent_1").last_heartbeat
        assert updated_heartbeat > initial_heartbeat


class TestAgentHealthValidation:
    """Test agent health validation."""
    
    def test_validate_agent_health_all_healthy(self):
        """Test validation when all agents are healthy."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.register_agent("agent_2", "Leaf_Verifier")
        
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.update_agent_health("agent_2", AgentStatus.HEALTHY, True, 0)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is True
        assert len(unhealthy) == 0
    
    def test_validate_agent_health_one_unhealthy(self):
        """Test validation when one agent is unhealthy."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.register_agent("agent_2", "Leaf_Verifier")
        
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.update_agent_health("agent_2", AgentStatus.UNHEALTHY, False, 1)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is False
        assert len(unhealthy) == 1
        assert unhealthy[0].agent_id == "agent_2"
    
    def test_validate_agent_health_not_responsive(self):
        """Test validation when agent is not responsive."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, False, 0)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is False
        assert len(unhealthy) == 1
    
    def test_validate_agent_health_with_errors(self):
        """Test validation when agent has errors."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 3)
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is False
        assert len(unhealthy) == 1
    
    def test_validate_agent_health_no_agents(self):
        """Test validation when no agents are registered."""
        module = TransitionValidationModule()
        
        all_healthy, unhealthy = module.validate_agent_health()
        assert all_healthy is True
        assert len(unhealthy) == 0


class TestBootstrapCompletion:
    """Test bootstrap completion tracking."""
    
    def test_mark_bootstrap_complete(self):
        """Test marking bootstrap as complete."""
        module = TransitionValidationModule()
        
        is_complete, _ = module.validate_bootstrap_completion()
        assert is_complete is False
        
        module.mark_bootstrap_complete()
        
        is_complete, _ = module.validate_bootstrap_completion()
        assert is_complete is True
    
    def test_bootstrap_completion_message(self):
        """Test bootstrap completion message."""
        module = TransitionValidationModule()
        
        module.mark_bootstrap_complete()
        is_complete, details = module.validate_bootstrap_completion()
        
        assert is_complete is True
        assert "complete" in details.lower()


class TestMemoryConsistency:
    """Test memory consistency tracking."""
    
    def test_set_memory_consistent(self):
        """Test setting memory as consistent."""
        module = TransitionValidationModule()
        
        module.set_memory_consistency(True)
        is_consistent, _ = module.validate_memory_consistency()
        assert is_consistent is True
    
    def test_set_memory_inconsistent(self):
        """Test setting memory as inconsistent."""
        module = TransitionValidationModule()
        
        module.set_memory_consistency(False)
        is_consistent, _ = module.validate_memory_consistency()
        assert is_consistent is False
    
    def test_memory_consistency_message(self):
        """Test memory consistency message."""
        module = TransitionValidationModule()
        
        module.set_memory_consistency(False)
        is_consistent, details = module.validate_memory_consistency()
        
        assert is_consistent is False
        assert "failed" in details.lower()


class TestTransitionValidation:
    """Test mode transition validation."""
    
    def test_validate_day1_to_day2_all_checks_pass(self):
        """Test DAY1 to DAY2 transition when all checks pass."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is True
        assert result.all_agents_healthy is True
        assert result.memory_consistent is True
        assert result.bootstrap_complete is True
        assert len(result.checks_passed) == 3
        assert len(result.checks_failed) == 0
        assert result.error_message is None
    
    def test_validate_day1_to_day2_agent_health_fails(self):
        """Test DAY1 to DAY2 transition when agent health check fails."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.UNHEALTHY, False, 1)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert result.all_agents_healthy is False
        assert len(result.checks_failed) == 1
        assert result.checks_failed[0].check_type == ValidationCheckType.AGENT_HEALTH
        assert "agent_health" in result.error_message.lower()
    
    def test_validate_day1_to_day2_memory_fails(self):
        """Test DAY1 to DAY2 transition when memory consistency check fails."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(False)
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert result.memory_consistent is False
        assert len(result.checks_failed) == 1
        assert result.checks_failed[0].check_type == ValidationCheckType.MEMORY_CONSISTENCY
    
    def test_validate_day1_to_day2_bootstrap_fails(self):
        """Test DAY1 to DAY2 transition when bootstrap completion check fails."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.set_memory_consistency(True)
        # Don't mark bootstrap complete
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert result.bootstrap_complete is False
        assert len(result.checks_failed) == 1
        assert result.checks_failed[0].check_type == ValidationCheckType.BOOTSTRAP_COMPLETION
    
    def test_validate_day1_to_day2_multiple_failures(self):
        """Test DAY1 to DAY2 transition with multiple check failures."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.UNHEALTHY, False, 1)
        module.set_memory_consistency(False)
        # Don't mark bootstrap complete
        
        result = module.validate_transition("DAY1", "DAY2")
        
        assert result.is_valid is False
        assert len(result.checks_failed) == 3
        assert "agent_health" in result.error_message.lower()
        assert "memory_consistency" in result.error_message.lower()
        assert "bootstrap_completion" in result.error_message.lower()
    
    def test_validate_other_transitions_always_valid(self):
        """Test that other transitions don't require validation."""
        module = TransitionValidationModule()
        
        # BOOTSTRAP to DAY1 should always be valid
        result = module.validate_transition("BOOTSTRAP", "DAY1")
        assert result.is_valid is True
        assert len(result.checks_passed) == 0
        assert len(result.checks_failed) == 0
        
        # BOOTSTRAP to DAY2 should always be valid
        result = module.validate_transition("BOOTSTRAP", "DAY2")
        assert result.is_valid is True
    
    def test_validate_transition_records_timestamp(self):
        """Test that transition validation records timestamp."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        before = time.time()
        result = module.validate_transition("DAY1", "DAY2")
        after = time.time()
        
        assert before <= result.timestamp <= after
    
    def test_validate_transition_stores_in_history(self):
        """Test that validation results are stored in history."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        result1 = module.validate_transition("DAY1", "DAY2")
        result2 = module.validate_transition("BOOTSTRAP", "DAY1")
        
        history = module.get_validation_history()
        assert len(history) == 2
        assert history[0] == result1
        assert history[1] == result2


class TestValidationHistory:
    """Test validation history tracking."""
    
    def test_get_validation_history_empty(self):
        """Test getting validation history when empty."""
        module = TransitionValidationModule()
        history = module.get_validation_history()
        assert history == []
    
    def test_get_validation_history_multiple_entries(self):
        """Test getting validation history with multiple entries."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        module.validate_transition("DAY1", "DAY2")
        module.validate_transition("BOOTSTRAP", "DAY1")
        module.validate_transition("DAY1", "DAY2")
        
        history = module.get_validation_history()
        assert len(history) == 3
    
    def test_validation_history_is_immutable(self):
        """Test that validation history cannot be modified externally."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        module.validate_transition("DAY1", "DAY2")
        
        history1 = module.get_validation_history()
        history1.append(None)  # Try to modify
        
        history2 = module.get_validation_history()
        assert len(history2) == 1  # Should not be modified


class TestResetValidationState:
    """Test resetting validation state."""
    
    def test_reset_clears_agents(self):
        """Test that reset clears agent registry."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        
        assert len(module.get_all_agents_status()) == 1
        
        module.reset_validation_state()
        
        assert len(module.get_all_agents_status()) == 0
    
    def test_reset_clears_history(self):
        """Test that reset clears validation history."""
        module = TransitionValidationModule()
        module.register_agent("agent_1", "Leaf_Builder")
        module.update_agent_health("agent_1", AgentStatus.HEALTHY, True, 0)
        module.mark_bootstrap_complete()
        module.set_memory_consistency(True)
        
        module.validate_transition("DAY1", "DAY2")
        assert len(module.get_validation_history()) == 1
        
        module.reset_validation_state()
        
        assert len(module.get_validation_history()) == 0
    
    def test_reset_resets_bootstrap_state(self):
        """Test that reset resets bootstrap completion state."""
        module = TransitionValidationModule()
        module.mark_bootstrap_complete()
        
        is_complete, _ = module.validate_bootstrap_completion()
        assert is_complete is True
        
        module.reset_validation_state()
        
        is_complete, _ = module.validate_bootstrap_completion()
        assert is_complete is False
    
    def test_reset_resets_memory_state(self):
        """Test that reset resets memory consistency state."""
        module = TransitionValidationModule()
        module.set_memory_consistency(False)
        
        is_consistent, _ = module.validate_memory_consistency()
        assert is_consistent is False
        
        module.reset_validation_state()
        
        is_consistent, _ = module.validate_memory_consistency()
        assert is_consistent is True
