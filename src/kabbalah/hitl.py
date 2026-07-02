"""Human-in-the-loop approval gate.

The HITL layer is intentionally non-interactive by default. Production callers
must inject an approval provider backed by UI, ticketing, CLI, or another
operator workflow. Without a provider, high-risk requests remain pending and are
not auto-approved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ApprovalStatus(Enum):
    """HITL decision status."""

    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"
    ERROR = "error"


class NivelUrgencia(Enum):
    """Urgency level for HITL requests."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


@dataclass(frozen=True)
class ApprovalRequest:
    """Request requiring human/operator approval."""

    agente_id: str
    acao: str
    risco: float
    contexto: Dict[str, Any]
    trace_id: str
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass(frozen=True)
class ApprovalDecision:
    """Result of a HITL approval request."""

    aprovado: bool
    status: ApprovalStatus
    trace_id: str
    motivo: str
    agente_id: str
    acao: str
    risco: float
    decided_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


ApprovalProvider = Callable[[ApprovalRequest], bool]


class HITL:
    """Human-in-the-loop approval service with immutable audit snapshots."""

    def __init__(self, approval_provider: Optional[ApprovalProvider] = None):
        self._approval_provider = approval_provider
        self._audit_log: List[ApprovalDecision] = []

    @property
    def audit_log(self) -> List[ApprovalDecision]:
        """Return a copy of the approval audit log."""

        return list(self._audit_log)

    def solicitar_aprovacao(self, request: ApprovalRequest) -> ApprovalDecision:
        """Request explicit approval for a high-risk operation."""

        if self._approval_provider is None:
            decision = ApprovalDecision(
                aprovado=False,
                status=ApprovalStatus.PENDING,
                trace_id=request.trace_id,
                motivo="No approval provider configured for non-interactive runtime",
                agente_id=request.agente_id,
                acao=request.acao,
                risco=request.risco,
            )
            self._audit_log.append(decision)
            return decision

        try:
            approved = bool(self._approval_provider(request))
            decision = ApprovalDecision(
                aprovado=approved,
                status=ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED,
                trace_id=request.trace_id,
                motivo="Approved by HITL provider" if approved else "Denied by HITL provider",
                agente_id=request.agente_id,
                acao=request.acao,
                risco=request.risco,
            )
        except Exception as exc:
            decision = ApprovalDecision(
                aprovado=False,
                status=ApprovalStatus.ERROR,
                trace_id=request.trace_id,
                motivo=f"Approval provider error: {exc}",
                agente_id=request.agente_id,
                acao=request.acao,
                risco=request.risco,
            )

        self._audit_log.append(decision)
        return decision

    def solicitar(
        self,
        *,
        agente_id: str,
        acao: Any,
        risco: float,
        contexto: Dict[str, Any],
        trace_id: str,
        urgencia: NivelUrgencia = NivelUrgencia.MEDIA,
    ) -> ApprovalDecision:
        """Synchronous bridge-friendly approval wrapper."""

        action_value = getattr(acao, "value", str(acao))
        request_context = dict(contexto)
        request_context["urgencia"] = urgencia.value
        return self.solicitar_aprovacao(
            ApprovalRequest(
                agente_id=agente_id,
                acao=action_value,
                risco=risco,
                contexto=request_context,
                trace_id=trace_id,
            )
        )

    async def solicitar_async(
        self,
        *,
        agente_id: str,
        acao: Any,
        risco: float,
        contexto: Dict[str, Any],
        trace_id: str,
        urgencia: NivelUrgencia = NivelUrgencia.MEDIA,
    ) -> ApprovalDecision:
        """Async wrapper for MCP servers that need awaitable HITL calls."""

        return self.solicitar(
            agente_id=agente_id,
            acao=acao,
            risco=risco,
            contexto=contexto,
            trace_id=trace_id,
            urgencia=urgencia,
        )
