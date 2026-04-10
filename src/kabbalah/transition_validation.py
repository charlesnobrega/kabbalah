"""Transition Validation Module for Day 2 Operations Compliance.

This module validates prerequisites before transitioning between operational modes,
particularly for DAY1 to DAY2 transitions. It checks agent health, memory consistency,
and bootstrap operation completion.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import time


class AgentStatus(Enum):
    """Status of an agent."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    DEGRADED = "degraded"


class ValidationCheckType(Enum):
    """Types of validation checks."""
    AGENT_HEALTH = "agent_health"
    MEMORY_CONSISTENCY = "memory_consistency"
    BOOTSTRAP_COMPLETION = "bootstrap_completion"
    SYSTEM_READINESS = "system_readiness"


@dataclass
class AgentHealthStatus:
    """Health status of an agent."""
    agent_id: str
    agent_role: str
    status: AgentStatus
    last_heartbeat: float
    is_responsive: bool
    error_count: int = 0
    warning_count: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ValidationCheckResult:
    """Result of a validation check."""
    check_type: ValidationCheckType
    passed: bool
    timestamp: float
    details: str
    affected_components: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class TransitionValidationResult:
    """Result of transition validation."""
    is_valid: bool
    timestamp: float
    from_mode: str
    to_mode: str
    checks_passed: List[ValidationCheckResult] = field(default_factory=list)
    checks_failed: List[ValidationCheckResult] = field(default_factory=list)
    all_agents_healthy: bool = False
    memory_consistent: bool = False
    bootstrap_complete: bool = False
    error_message: Optional[str] = None


class TransitionValidationModule:
    """Validates prerequisites for mode transitions."""
    
    def __init__(self):
        """Initialize TransitionValidationModule."""
        self._agent_registry: Dict[str, AgentHealthStatus] = {}
        self._validation_history: List[TransitionValidationResult] = []
        self._bootstrap_operations_completed: bool = False
        self._memory_consistency_state: bool = True
    
    def register_agent(
        self,
        agent_id: str,
        agent_role: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Register an agent for health monitoring.
        
        Args:
            agent_id: Unique agent identifier
            agent_role: Canonical role of the agent
            metadata: Optional metadata about the agent
        """
        if not agent_id:
            raise ValueError("agent_id cannot be empty")
        
        if not agent_role:
            raise ValueError("agent_role cannot be empty")
        
        self._agent_registry[agent_id] = AgentHealthStatus(
            agent_id=agent_id,
            agent_role=agent_role,
            status=AgentStatus.INITIALIZING,
            last_heartbeat=time.time(),
            is_responsive=False,
            metadata=metadata or {}
        )
    
    def update_agent_health(
        self,
        agent_id: str,
        status: AgentStatus,
        is_responsive: bool,
        error_count: int = 0,
        warning_count: int = 0
    ) -> None:
        """
        Update health status of an agent.
        
        Args:
            agent_id: Agent identifier
            status: Current health status
            is_responsive: Whether agent is responsive
            error_count: Number of errors
            warning_count: Number of warnings
        """
        if agent_id not in self._agent_registry:
            raise ValueError(f"Agent {agent_id} not registered")
        
        agent = self._agent_registry[agent_id]
        agent.status = status
        agent.is_responsive = is_responsive
        agent.error_count = error_count
        agent.warning_count = warning_count
        agent.last_heartbeat = time.time()
    
    def mark_bootstrap_complete(self) -> None:
        """Mark that all bootstrap operations are complete."""
        self._bootstrap_operations_completed = True
    
    def set_memory_consistency(self, is_consistent: bool) -> None:
        """
        Set memory consistency state.
        
        Args:
            is_consistent: Whether memory is consistent
        """
        self._memory_consistency_state = is_consistent
    
    def validate_agent_health(self) -> Tuple[bool, List[AgentHealthStatus]]:
        """
        Validate that all registered agents are healthy.
        
        Returns:
            (all_healthy, unhealthy_agents)
        """
        unhealthy_agents = []
        
        for agent_id, agent in self._agent_registry.items():
            # Agent is healthy if:
            # 1. Status is HEALTHY
            # 2. Agent is responsive
            # 3. No critical errors (error_count == 0)
            is_healthy = (
                agent.status == AgentStatus.HEALTHY and
                agent.is_responsive and
                agent.error_count == 0
            )
            
            if not is_healthy:
                unhealthy_agents.append(agent)
        
        all_healthy = len(unhealthy_agents) == 0
        return all_healthy, unhealthy_agents
    
    def validate_memory_consistency(self) -> Tuple[bool, str]:
        """
        Validate that memory is consistent.
        
        Returns:
            (is_consistent, details)
        """
        if self._memory_consistency_state:
            return True, "Memory is consistent"
        else:
            return False, "Memory consistency check failed"
    
    def validate_bootstrap_completion(self) -> Tuple[bool, str]:
        """
        Validate that all bootstrap operations are complete.
        
        Returns:
            (is_complete, details)
        """
        if self._bootstrap_operations_completed:
            return True, "All bootstrap operations are complete"
        else:
            return False, "Bootstrap operations are still pending"
    
    def validate_transition(
        self,
        from_mode: str,
        to_mode: str
    ) -> TransitionValidationResult:
        """
        Validate prerequisites for a mode transition.
        
        Args:
            from_mode: Current operational mode
            to_mode: Target operational mode
            
        Returns:
            TransitionValidationResult with validation details
        """
        result = TransitionValidationResult(
            is_valid=True,
            timestamp=time.time(),
            from_mode=from_mode,
            to_mode=to_mode
        )
        
        # DAY1 to DAY2 transition requires all checks
        if from_mode == "DAY1" and to_mode == "DAY2":
            # Check 1: Agent health
            agents_healthy, unhealthy_agents = self.validate_agent_health()
            health_check = ValidationCheckResult(
                check_type=ValidationCheckType.AGENT_HEALTH,
                passed=agents_healthy,
                timestamp=time.time(),
                details=f"Agent health check: {len(self._agent_registry)} agents registered, "
                        f"{len(unhealthy_agents)} unhealthy",
                affected_components=[a.agent_id for a in unhealthy_agents]
            )
            
            if agents_healthy:
                result.checks_passed.append(health_check)
            else:
                result.checks_failed.append(health_check)
                result.is_valid = False
            
            result.all_agents_healthy = agents_healthy
            
            # Check 2: Memory consistency
            memory_consistent, memory_details = self.validate_memory_consistency()
            memory_check = ValidationCheckResult(
                check_type=ValidationCheckType.MEMORY_CONSISTENCY,
                passed=memory_consistent,
                timestamp=time.time(),
                details=memory_details
            )
            
            if memory_consistent:
                result.checks_passed.append(memory_check)
            else:
                result.checks_failed.append(memory_check)
                result.is_valid = False
            
            result.memory_consistent = memory_consistent
            
            # Check 3: Bootstrap completion
            bootstrap_complete, bootstrap_details = self.validate_bootstrap_completion()
            bootstrap_check = ValidationCheckResult(
                check_type=ValidationCheckType.BOOTSTRAP_COMPLETION,
                passed=bootstrap_complete,
                timestamp=time.time(),
                details=bootstrap_details
            )
            
            if bootstrap_complete:
                result.checks_passed.append(bootstrap_check)
            else:
                result.checks_failed.append(bootstrap_check)
                result.is_valid = False
            
            result.bootstrap_complete = bootstrap_complete
            
            # Set error message if validation failed
            if not result.is_valid:
                failed_checks = [c.check_type.value for c in result.checks_failed]
                result.error_message = (
                    f"Transition from {from_mode} to {to_mode} failed. "
                    f"Failed checks: {', '.join(failed_checks)}"
                )
        
        # Other transitions don't require validation
        else:
            result.is_valid = True
            result.error_message = None
        
        # Store in history
        self._validation_history.append(result)
        
        return result
    
    def get_validation_history(self) -> List[TransitionValidationResult]:
        """
        Get history of all validation attempts.
        
        Returns:
            List of validation results
        """
        return list(self._validation_history)
    
    def get_agent_status(self, agent_id: str) -> Optional[AgentHealthStatus]:
        """
        Get current health status of an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentHealthStatus or None if not found
        """
        return self._agent_registry.get(agent_id)
    
    def get_all_agents_status(self) -> Dict[str, AgentHealthStatus]:
        """
        Get health status of all registered agents.
        
        Returns:
            Dictionary mapping agent_id to AgentHealthStatus
        """
        return dict(self._agent_registry)
    
    def reset_validation_state(self) -> None:
        """Reset validation state for testing."""
        self._agent_registry.clear()
        self._validation_history.clear()
        self._bootstrap_operations_completed = False
        self._memory_consistency_state = True
