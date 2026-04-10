"""Domain Orchestrator for coordinating execution within a domain."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time


class SpawnError(Exception):
    """Raised when leaf node spawning fails."""
    pass


class DomainExecutionError(Exception):
    """Raised when domain execution fails."""
    pass


@dataclass
class LeafNode:
    """Leaf node for executing concrete tasks."""
    run_id: str
    branch_id: str
    leaf_id: str
    trace_id: str  # run_id:branch_id:leaf_id
    task_id: str
    task_type: str
    description: str
    provider: str
    model: str
    tools: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 3
    metadata: Dict = field(default_factory=dict)


@dataclass
class LeafResult:
    """Result from leaf node execution."""
    run_id: str
    branch_id: str
    leaf_id: str
    trace_id: str
    task_id: str
    status: str  # success, error, timeout
    artifacts: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0


class DomainOrchestrator:
    """Orchestrates execution within a domain."""
    
    _leaf_counter = {}  # Track leaf counters per domain
    _last_date = None
    
    def __init__(self):
        """Initialize DomainOrchestrator."""
        pass
    
    def spawn_leaf_nodes(
        self,
        branch,
        run_id: str,
        branch_id: str
    ) -> List[LeafNode]:
        """
        Spawn leaf nodes for domain tasks.
        
        Args:
            branch: Domain branch specification
            run_id: Execution identifier
            branch_id: Branch identifier
            
        Returns:
            List of spawned leaf nodes
            
        Raises:
            SpawnError: If leaf node creation fails
        """
        if not branch:
            raise SpawnError("Branch cannot be null")
        
        if not run_id:
            raise SpawnError("run_id cannot be null")
        
        if not branch_id:
            raise SpawnError("branch_id cannot be null")
        
        if not hasattr(branch, 'tasks') or not branch.tasks:
            raise SpawnError("Branch must have at least one task")
        
        try:
            leaf_nodes = []
            
            for task in branch.tasks:
                leaf_id = self._generate_leaf_id(branch.domain_name)
                trace_id = f"{run_id}:{branch_id}:{leaf_id}"
                
                # Create leaf node
                leaf_node = LeafNode(
                    run_id=run_id,
                    branch_id=branch_id,
                    leaf_id=leaf_id,
                    trace_id=trace_id,
                    task_id=task.get("task_id", f"task_{leaf_id}"),
                    task_type=task.get("task_type", "implementation"),
                    description=task.get("description", ""),
                    provider=branch.provider,
                    model=branch.model,
                    tools=task.get("tools", []),
                    timeout=task.get("timeout", 300),
                    retry_count=task.get("retry_count", 3),
                    metadata={
                        "created_at": time.time(),
                        "domain": branch.domain_name,
                        "task_inputs": task.get("inputs", {}),
                        "expected_outputs": task.get("expected_outputs", {})
                    }
                )
                
                leaf_nodes.append(leaf_node)
            
            # Validate leaf nodes
            self._validate_leaf_nodes(leaf_nodes)
            
            return leaf_nodes
        
        except Exception as e:
            if isinstance(e, SpawnError):
                raise
            raise SpawnError(f"Failed to spawn leaf nodes: {str(e)}")
    
    def execute_leaf_nodes(
        self,
        leaf_nodes: List[LeafNode]
    ) -> List[LeafResult]:
        """
        Execute leaf nodes in parallel or sequentially.
        
        Args:
            leaf_nodes: Leaf nodes to execute
            
        Returns:
            List of execution results
            
        Raises:
            DomainExecutionError: If execution fails
        """
        if not leaf_nodes:
            raise DomainExecutionError("Leaf nodes list cannot be empty")
        
        try:
            results = []
            
            # Execute leaf nodes (in parallel in real implementation)
            for leaf_node in leaf_nodes:
                result = self._execute_leaf_node(leaf_node)
                results.append(result)
            
            return results
        
        except Exception as e:
            if isinstance(e, DomainExecutionError):
                raise
            raise DomainExecutionError(f"Failed to execute leaf nodes: {str(e)}")
    
    def _generate_leaf_id(self, domain: str) -> str:
        """Generate unique leaf_id for domain.
        
        Format: leaf_{domain}_{NNN}
        """
        from datetime import datetime
        
        today = datetime.utcnow().strftime("%Y_%m_%d")
        
        # Reset counter if date changed
        if today != DomainOrchestrator._last_date:
            DomainOrchestrator._last_date = today
            DomainOrchestrator._leaf_counter = {}
        
        # Get counter for this domain
        if domain not in DomainOrchestrator._leaf_counter:
            DomainOrchestrator._leaf_counter[domain] = 0
        
        DomainOrchestrator._leaf_counter[domain] += 1
        counter = DomainOrchestrator._leaf_counter[domain]
        
        return f"leaf_{domain}_{counter:03d}"
    
    def _validate_leaf_nodes(self, leaf_nodes: List[LeafNode]) -> None:
        """Validate that all leaf nodes are valid."""
        leaf_ids = set()
        
        for leaf_node in leaf_nodes:
            # Check leaf_id format
            if not leaf_node.leaf_id.startswith("leaf_"):
                raise SpawnError(f"Invalid leaf_id format: {leaf_node.leaf_id}")
            
            # Check uniqueness
            if leaf_node.leaf_id in leaf_ids:
                raise SpawnError(f"Duplicate leaf_id: {leaf_node.leaf_id}")
            
            leaf_ids.add(leaf_node.leaf_id)
            
            # Check trace_id format
            if not leaf_node.trace_id:
                raise SpawnError(f"Invalid trace_id: {leaf_node.trace_id}")
            
            parts = leaf_node.trace_id.split(":")
            if len(parts) != 3:
                raise SpawnError(f"Invalid trace_id format: {leaf_node.trace_id}")
    
    def _execute_leaf_node(self, leaf_node: LeafNode) -> LeafResult:
        """Execute a single leaf node."""
        start_time = time.time()
        
        try:
            # In a real implementation, this would execute the task
            # using the assigned provider and tools
            end_time = time.time()
            
            return LeafResult(
                run_id=leaf_node.run_id,
                branch_id=leaf_node.branch_id,
                leaf_id=leaf_node.leaf_id,
                trace_id=leaf_node.trace_id,
                task_id=leaf_node.task_id,
                status="success",
                artifacts=[],
                metadata={},
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time
            )
        
        except Exception as e:
            end_time = time.time()
            return LeafResult(
                run_id=leaf_node.run_id,
                branch_id=leaf_node.branch_id,
                leaf_id=leaf_node.leaf_id,
                trace_id=leaf_node.trace_id,
                task_id=leaf_node.task_id,
                status="error",
                artifacts=[],
                metadata={"error": str(e)},
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time
            )
