"""Data models for Kabbalah orchestration system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class UserRequest:
    """User's project request."""
    project_name: str
    project_description: str
    scope: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Specification:
    """Premium project specification."""
    run_id: str
    project_name: str
    project_description: str
    scope: str
    constraints: List[str]
    resources: Dict[str, Any]
    domains: List[str]
    dependencies: Dict[str, List[str]]
    metadata: Dict[str, Any]
    created_at: float
    version: str = "1.0"
