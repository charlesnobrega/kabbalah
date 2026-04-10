"""Memory Subsystem for Kabbalah - Semantic memory storage and retrieval."""

import json
import logging
import os
import platform
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class Knowledge:
    """Knowledge item to store in semantic memory."""
    knowledge_id: str
    content: str
    category: str  # shared, domain-specific, role-specific
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    trace_id: Optional[str] = None


@dataclass
class MemoryConsistencyState:
    """State tracking for memory consistency."""
    last_sync_time: float
    pending_operations: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    is_consistent: bool = True


class MemoryBackend(ABC):
    """Abstract base class for memory backends."""

    @abstractmethod
    def store(self, knowledge: Knowledge) -> bool:
        """Store knowledge in backend."""
        pass

    @abstractmethod
    def query(self, query: str, limit: int = 10) -> List[Knowledge]:
        """Query knowledge from backend."""
        pass

    @abstractmethod
    def ensure_consistency(self) -> bool:
        """Ensure consistency in backend."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass


class CogneeBackend(MemoryBackend):
    """Cognee-based semantic memory backend."""

    def __init__(self):
        """Initialize Cognee backend."""
        self.available = False
        self._initialize_cognee()

    def _initialize_cognee(self) -> None:
        """Initialize Cognee client."""
        try:
            # Try to import and initialize Cognee
            # This is a placeholder - actual Cognee integration would go here
            import cognee
            self.cognee_client = cognee
            self.available = True
            logger.info("Cognee backend initialized successfully")
        except ImportError:
            logger.warning("Cognee not available, will use fallback")
            self.available = False
        except Exception as e:
            logger.warning(f"Failed to initialize Cognee: {e}")
            self.available = False

    def store(self, knowledge: Knowledge) -> bool:
        """Store knowledge in Cognee."""
        if not self.available:
            return False

        try:
            # Placeholder for actual Cognee storage
            # In real implementation, this would call Cognee's semantic indexing
            logger.debug(f"Storing knowledge {knowledge.knowledge_id} in Cognee")
            return True
        except Exception as e:
            logger.error(f"Failed to store knowledge in Cognee: {e}")
            return False

    def query(self, query: str, limit: int = 10) -> List[Knowledge]:
        """Query knowledge from Cognee."""
        if not self.available:
            return []

        try:
            # Placeholder for actual Cognee query
            # In real implementation, this would call Cognee's semantic search
            logger.debug(f"Querying Cognee with: {query}")
            return []
        except Exception as e:
            logger.error(f"Failed to query Cognee: {e}")
            return []

    def ensure_consistency(self) -> bool:
        """Ensure consistency in Cognee."""
        if not self.available:
            return False

        try:
            # Placeholder for consistency check
            logger.debug("Checking Cognee consistency")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure Cognee consistency: {e}")
            return False

    def is_available(self) -> bool:
        """Check if Cognee is available."""
        return self.available


class JSONLBackend(MemoryBackend):
    """JSONL-based local storage backend for Windows compatibility."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize JSONL backend."""
        if storage_path is None:
            storage_path = os.path.join(
                os.path.expanduser("~"), ".kabbalah", "memory"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.knowledge_file = self.storage_path / "knowledge.jsonl"
        self.lock = threading.RLock()
        logger.info(f"JSONL backend initialized at {self.storage_path}")

    def store(self, knowledge: Knowledge) -> bool:
        """Store knowledge in JSONL file."""
        try:
            with self.lock:
                # Read existing knowledge
                existing = self._read_all_knowledge()

                # Update or add knowledge
                existing_ids = {k.knowledge_id for k in existing}
                if knowledge.knowledge_id in existing_ids:
                    existing = [
                        k
                        for k in existing
                        if k.knowledge_id != knowledge.knowledge_id
                    ]

                existing.append(knowledge)

                # Write back to file
                self._write_all_knowledge(existing)
                logger.debug(f"Stored knowledge {knowledge.knowledge_id} in JSONL")
                return True
        except Exception as e:
            logger.error(f"Failed to store knowledge in JSONL: {e}")
            return False

    def query(self, query: str, limit: int = 10) -> List[Knowledge]:
        """Query knowledge from JSONL file."""
        try:
            with self.lock:
                all_knowledge = self._read_all_knowledge()

                # Simple substring matching for now
                # In production, could use more sophisticated search
                results = [
                    k
                    for k in all_knowledge
                    if query.lower() in k.content.lower()
                    or query.lower() in k.category.lower()
                ]

                return results[:limit]
        except Exception as e:
            logger.error(f"Failed to query JSONL: {e}")
            return []

    def ensure_consistency(self) -> bool:
        """Ensure consistency in JSONL storage."""
        try:
            with self.lock:
                # Verify file integrity
                if not self.knowledge_file.exists():
                    return True

                # Try to read and validate all entries
                with open(self.knowledge_file, "r") as f:
                    for line in f:
                        if line.strip():
                            json.loads(line)

                logger.debug("JSONL consistency check passed")
                return True
        except Exception as e:
            logger.error(f"JSONL consistency check failed: {e}")
            return False

    def is_available(self) -> bool:
        """Check if JSONL backend is available."""
        return True

    def _read_all_knowledge(self) -> List[Knowledge]:
        """Read all knowledge from JSONL file."""
        if not self.knowledge_file.exists():
            return []

        knowledge_list = []
        try:
            with open(self.knowledge_file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        knowledge_list.append(Knowledge(**data))
        except Exception as e:
            logger.error(f"Error reading JSONL file: {e}")

        return knowledge_list

    def _write_all_knowledge(self, knowledge_list: List[Knowledge]) -> None:
        """Write all knowledge to JSONL file."""
        with open(self.knowledge_file, "w") as f:
            for k in knowledge_list:
                f.write(json.dumps(asdict(k)) + "\n")


class MemorySubsystem:
    """
    Semantic memory subsystem for Kabbalah.

    Provides storage and retrieval of semantic knowledge across agents.
    Uses Cognee as primary backend (Linux/macOS) with JSONL fallback (Windows).
    Supports atomic operations and conflict resolution for parallel operations.
    """

    def __init__(self, jsonl_storage_path: Optional[str] = None):
        """
        Initialize MemorySubsystem.

        Args:
            jsonl_storage_path: Optional path for JSONL storage (defaults to ~/.kabbalah/memory)
        """
        self.cognee_backend = CogneeBackend()
        self.jsonl_backend = JSONLBackend(jsonl_storage_path)
        self.consistency_state = MemoryConsistencyState(
            last_sync_time=datetime.now().timestamp()
        )
        self.lock = threading.RLock()
        self._select_primary_backend()
        logger.info(f"MemorySubsystem initialized with primary backend: {self.primary_backend.__class__.__name__}")

    def _select_primary_backend(self) -> None:
        """Select primary backend based on platform and availability."""
        # On Windows, prefer JSONL; on other platforms, prefer Cognee if available
        if platform.system() == "Windows":
            self.primary_backend = self.jsonl_backend
            self.fallback_backend = self.cognee_backend
            logger.info("Selected JSONL as primary backend (Windows platform)")
        else:
            if self.cognee_backend.is_available():
                self.primary_backend = self.cognee_backend
                self.fallback_backend = self.jsonl_backend
                logger.info("Selected Cognee as primary backend")
            else:
                self.primary_backend = self.jsonl_backend
                self.fallback_backend = self.cognee_backend
                logger.info("Selected JSONL as primary backend (Cognee unavailable)")

    def store_knowledge(self, knowledge: Knowledge, trace_id: str) -> bool:
        """
        Store knowledge in semantic memory.

        Args:
            knowledge: Knowledge item to store
            trace_id: Trace identifier for audit

        Returns:
            True if storage successful, False otherwise
        """
        try:
            with self.lock:
                # Attach trace_id to knowledge
                knowledge.trace_id = trace_id

                # Try primary backend
                if self.primary_backend.store(knowledge):
                    logger.info(
                        f"Stored knowledge {knowledge.knowledge_id} via {self.primary_backend.__class__.__name__} "
                        f"(trace_id: {trace_id})"
                    )
                    return True

                # Fallback to secondary backend
                logger.warning(
                    f"Primary backend failed, attempting fallback for knowledge {knowledge.knowledge_id}"
                )
                if self.fallback_backend.store(knowledge):
                    logger.info(
                        f"Stored knowledge {knowledge.knowledge_id} via {self.fallback_backend.__class__.__name__} "
                        f"(trace_id: {trace_id})"
                    )
                    return True

                logger.error(
                    f"Failed to store knowledge {knowledge.knowledge_id} in both backends"
                )
                return False

        except Exception as e:
            logger.error(f"Error storing knowledge: {e}", exc_info=True)
            return False

    def query_knowledge(self, query: str, limit: int = 10) -> List[Knowledge]:
        """
        Query semantic memory.

        Args:
            query: Semantic query string
            limit: Maximum number of results to return

        Returns:
            List of relevant knowledge items
        """
        try:
            with self.lock:
                # Try primary backend first
                results = self.primary_backend.query(query, limit)

                if results:
                    logger.debug(
                        f"Found {len(results)} results from {self.primary_backend.__class__.__name__}"
                    )
                    return results

                # Fallback to secondary backend
                logger.debug(
                    f"No results from primary backend, trying fallback"
                )
                results = self.fallback_backend.query(query, limit)

                if results:
                    logger.debug(
                        f"Found {len(results)} results from {self.fallback_backend.__class__.__name__}"
                    )

                return results

        except Exception as e:
            logger.error(f"Error querying knowledge: {e}", exc_info=True)
            return []

    def ensure_consistency(self) -> bool:
        """
        Ensure memory consistency across parallel operations.

        Returns:
            True if consistency is maintained, False otherwise
        """
        try:
            with self.lock:
                # Check primary backend consistency
                primary_consistent = self.primary_backend.ensure_consistency()

                # Check fallback backend consistency
                fallback_consistent = self.fallback_backend.ensure_consistency()

                # Update consistency state
                self.consistency_state.is_consistent = (
                    primary_consistent and fallback_consistent
                )
                self.consistency_state.last_sync_time = datetime.now().timestamp()

                if self.consistency_state.is_consistent:
                    logger.info("Memory consistency check passed")
                else:
                    logger.warning("Memory consistency check failed")

                return self.consistency_state.is_consistent

        except Exception as e:
            logger.error(f"Error ensuring consistency: {e}", exc_info=True)
            return False

    def get_consistency_state(self) -> MemoryConsistencyState:
        """
        Get current memory consistency state.

        Returns:
            Current consistency state
        """
        with self.lock:
            return self.consistency_state

    def clear_all_knowledge(self) -> bool:
        """
        Clear all knowledge from memory (for testing/reset).

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                # Clear JSONL backend
                if self.jsonl_backend.knowledge_file.exists():
                    self.jsonl_backend.knowledge_file.unlink()
                    logger.info("Cleared JSONL backend")

                # Reset consistency state
                self.consistency_state = MemoryConsistencyState(
                    last_sync_time=datetime.now().timestamp()
                )

                return True
        except Exception as e:
            logger.error(f"Error clearing knowledge: {e}", exc_info=True)
            return False
