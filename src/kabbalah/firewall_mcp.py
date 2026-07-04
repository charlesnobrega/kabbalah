"""Firewall for MCP/tool authorization.

The firewall centralizes RBAC, contract validation, risk assessment, HITL, trace
metadata, and auditable decisions before a tool/MCP operation is executed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .hitl import ApprovalRequest, HITL


class MCPRiskLevel(Enum):
    """Risk buckets for MCP/tool requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AcaoMCP(Enum):
    """Canonical MCP actions exposed by the Kabbalah/SillyTavern bridge."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_COMMAND = "execute_command"
    NETWORK_REQUEST = "network_request"
    READ_ENV_VAR = "read_env_var"
    CALL_TOOL = "call_tool"
    DATABASE_QUERY = "database_query"
    CHECK_HITL_STATUS = "check_hitl_status"
    PROPOSE_CONTRACT = "propose_contract"
    SIGN_CONTRACT = "sign_contract"
    REJECT_CONTRACT = "reject_contract"
    COMPLETE_TASK = "complete_task"
    GET_NETWORK_STATS = "get_network_stats"


@dataclass(frozen=True)
class RegraMCP:
    """Compatibility rule model for bridge-level MCP policy definitions."""

    acao: AcaoMCP
    allowed_roles: set[str] = field(default_factory=set)
    precisa_hitl: bool = False
    max_risk: float = 1.0


@dataclass(frozen=True)
class MCPRequest:
    """Authorization request for an MCP/tool call."""

    agente_id: str
    ferramenta: str
    argumentos: Dict[str, Any]
    contrato_id: str
    trace_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MCPDecision:
    """Authorization decision for an MCP/tool call."""

    autorizado: bool
    motivo: str
    trace_id: str
    agente_id: str
    ferramenta: str
    risk_level: MCPRiskLevel
    risk_score: float
    hitl_required: bool = False
    decided_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


CheckResult = Tuple[bool, Optional[str]]
RequestChecker = Callable[[MCPRequest], CheckResult]
RiskAssessor = Callable[[MCPRequest], Tuple[MCPRiskLevel, float, str]]
ContractVerifier = Callable[[str, str], bool]


def _deny_all(_: MCPRequest) -> CheckResult:
    return False, "Nenhum checker configurado — negado por padrão (fail-closed)"


def permitir_tudo(_: MCPRequest) -> CheckResult:
    """Explicit opt-in allow-all checker.

    Wave-6 hardening: the firewall denies by default when no checker is
    injected. Callers that intentionally delegate authorization elsewhere
    (e.g. the MCP bridge, which relies on contracts + risk + HITL) must make
    that permissiveness visible by passing this function explicitly.
    """

    return True, None


def _default_risk_assessor(request: MCPRequest) -> Tuple[MCPRiskLevel, float, str]:
    """Conservative keyword-based risk estimator for the initial implementation."""
    metadata_risk = request.metadata.get("risco")
    if metadata_risk is not None:
        risk_score = float(metadata_risk)
        if risk_score > 0.95:
            return MCPRiskLevel.CRITICAL, risk_score, "Intent evaluator marked request as critical risk"
        if risk_score > 0.60:
            return MCPRiskLevel.HIGH, risk_score, "Intent evaluator marked request as high risk"
        if risk_score > 0.45:
            return MCPRiskLevel.MEDIUM, risk_score, "Intent evaluator marked request for audit"
        return MCPRiskLevel.LOW, risk_score, "Intent evaluator marked request as low risk"

    tool = request.ferramenta.lower()
    serialized_args = " ".join(str(value).lower() for value in request.argumentos.values())
    combined = f"{tool} {serialized_args}"

    critical_terms = ("deploy", "delete", "remove", "drop", "reset", "force", "credential")
    high_terms = ("write", "exec", "shell", "mcp", "network", "secret", "token")

    if any(term in combined for term in critical_terms):
        return MCPRiskLevel.CRITICAL, 0.96, "Critical operation keyword detected"
    if any(term in combined for term in high_terms):
        return MCPRiskLevel.HIGH, 0.75, "High-risk tool capability detected"
    return MCPRiskLevel.LOW, 0.2, "No high-risk capability detected"


class FirewallMCP:
    """Authorizes MCP/tool calls before execution."""

    def __init__(
        self,
        rbac_checker: Optional[RequestChecker] = None,
        contract_checker: Optional[RequestChecker] = None,
        contract_verifier: Optional[ContractVerifier] = None,
        risk_assessor: Optional[RiskAssessor] = None,
        hitl: Optional[HITL] = None,
    ):
        self._rbac_checker = rbac_checker or _deny_all
        self._contract_checker = contract_checker or _deny_all
        self._contract_verifier = contract_verifier
        self._risk_assessor = risk_assessor or _default_risk_assessor
        self._hitl = hitl or HITL()
        self._audit_log: List[MCPDecision] = []
        self._callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], Any]]] = {}

    @property
    def audit_log(self) -> List[MCPDecision]:
        """Return a copy of the firewall audit log."""

        return list(self._audit_log)

    def autorizar(self, request: MCPRequest) -> MCPDecision:
        """Authorize a request using RBAC, contracts, risk, and HITL."""

        rbac_ok, rbac_reason = self._rbac_checker(request)
        risk_level, risk_score, risk_reason = self._risk_assessor(request)
        if not rbac_ok:
            return self._record(
                request,
                autorizado=False,
                motivo=rbac_reason or "RBAC denied request",
                risk_level=risk_level,
                risk_score=risk_score,
            )

        contract_ok, contract_reason = self._contract_checker(request)
        if contract_ok and request.metadata.get("envolve_outro_agente") and not request.metadata.get("contract_checked"):
            contract_ok = self.verificar_contrato(request.agente_id, request.ferramenta)
            contract_reason = None if contract_ok else "CONTRACT_REQUIRED"
        if not contract_ok:
            decision = self._record(
                request,
                autorizado=False,
                motivo=contract_reason or "Contract denied request",
                risk_level=risk_level,
                risk_score=risk_score,
            )
            self._emit(
                "bloqueio",
                {
                    "agente_id": request.agente_id,
                    "acao": request.ferramenta,
                    "motivo": decision.motivo,
                    "score": risk_score,
                },
            )
            return decision

        hitl_required = risk_level in {MCPRiskLevel.HIGH, MCPRiskLevel.CRITICAL}
        if hitl_required:
            approval = self._hitl.solicitar_aprovacao(
                ApprovalRequest(
                    agente_id=request.agente_id,
                    acao=f"autorizar:{request.ferramenta}",
                    risco=risk_score,
                    contexto={
                        "argumentos": request.argumentos,
                        "contrato_id": request.contrato_id,
                        "risk_level": risk_level.value,
                        "risk_reason": risk_reason,
                    },
                    trace_id=request.trace_id,
                )
            )
            if not approval.aprovado:
                return self._record(
                    request,
                    autorizado=False,
                    motivo=f"HITL approval required or denied: {approval.motivo}",
                    risk_level=risk_level,
                    risk_score=risk_score,
                    hitl_required=True,
                )

        return self._record(
            request,
            autorizado=True,
            motivo=risk_reason,
            risk_level=risk_level,
            risk_score=risk_score,
            hitl_required=hitl_required,
        )

    def _record(
        self,
        request: MCPRequest,
        *,
        autorizado: bool,
        motivo: str,
        risk_level: MCPRiskLevel,
        risk_score: float,
        hitl_required: bool = False,
    ) -> MCPDecision:
        decision = MCPDecision(
            autorizado=autorizado,
            motivo=motivo,
            trace_id=request.trace_id,
            agente_id=request.agente_id,
            ferramenta=request.ferramenta,
            risk_level=risk_level,
            risk_score=risk_score,
            hitl_required=hitl_required,
        )
        self._audit_log.append(decision)
        return decision

    def verificar_contrato(self, agente_id: str, acao: str) -> bool:
        """Check the configured contract checker for an agent/action pair."""

        if self._contract_verifier is not None:
            return bool(self._contract_verifier(agente_id, acao))
        request = MCPRequest(
            agente_id=agente_id,
            ferramenta=acao,
            argumentos={},
            contrato_id="contract-check",
            trace_id="contract-check",
            metadata={},
        )
        ok, _ = self._contract_checker(request)
        return ok

    def registrar_callback(self, evento: str, fn: Callable[[str, Dict[str, Any]], Any]) -> None:
        self._callbacks.setdefault(evento, []).append(fn)

    def _emit(self, evento: str, dados: Dict[str, Any]) -> None:
        for callback in self._callbacks.get(evento, []):
            callback(evento, dict(dados))
