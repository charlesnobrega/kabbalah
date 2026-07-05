#!/usr/bin/env python3
"""SillyTavern stdio MCP bridge for the Kabbalah security kernel.

The bridge exposes a small MCP server. Every tool call is intercepted by the
Kabbalah pipeline before execution:

1. Evaluate intent with qlipot.
2. Authorize through FirewallMCP with agent role, risk, and trace context.
3. Enforce HITL through the firewall/HITL integration.
4. Resolve secrets through CofreBitwarden only when explicitly requested.
5. Execute and return a JSON payload to SillyTavern.

All logs go to stderr to avoid corrupting stdio JSON-RPC.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import ipaddress
import json
import logging
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from kabbalah.budget_manager import BudgetLedger, BudgetManager
from kabbalah.cofre import CofreBitwarden, CofreError
from kabbalah.configuration_manager import ConfigurationManager
from kabbalah.contrato_store import ContratoStore
from kabbalah.contratos import Contratos, VerificationOutcome
from kabbalah.firewall_mcp import AcaoMCP, FirewallMCP, MCPRequest, permitir_tudo
from kabbalah.hitl import HITL, NivelUrgencia
from kabbalah.llm_gateway import LLMGateway
from kabbalah.model_comparison import compare_models as compare_model_outputs
from kabbalah.providers.factory import ProviderFactory
from kabbalah.qlipot import Qlipot
from kabbalah.sillytavern_group_chat import render_group_event as render_group_chat_event
from kabbalah.sync_hub import SyncHub

logging.basicConfig(
    level=os.environ.get("KABBALAH_LOG_LEVEL", "WARNING").upper(),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("kabbalah_mcp_bridge")

mcp = FastMCP("kabbalah_mcp")
CONTRACT_EXEMPT_ACTIONS = {
    "propose_contract",
    "sign_contract",
    "reject_contract",
    "complete_task",
    "check_hitl_status",
    "get_network_stats",
    "get_budget_stats",
    "get_config_status",
}


class BridgePolicyError(Exception):
    """Bridge policy denied a request before execution."""


class TicketStore:
    """SQLite-backed HITL ticket store."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def put(self, ticket_id: str, payload: Mapping[str, Any]) -> None:
        serialized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hitl_tickets(ticket_id, payload, created_at) VALUES (?, ?, ?)",
                (ticket_id, serialized, time.time()),
            )

    def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT payload FROM hitl_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row[0])


STATE_DB_PATH = Path(os.environ.get("KABBALAH_BRIDGE_STATE_DB", str(PROJECT_ROOT / ".kabbalah_bridge_state.sqlite3")))

hitl = HITL()
cofre = CofreBitwarden(use_cache=True)
qlipot = Qlipot()
contratos = Contratos(qlipot=qlipot, hitl=hitl, store=ContratoStore(STATE_DB_PATH))
tickets = TicketStore(STATE_DB_PATH)
budget_ledger = BudgetLedger(STATE_DB_PATH)
budget_manager = BudgetManager.from_env(budget_ledger)
config_manager = ConfigurationManager()
config_manager.load_defaults()
config_manager.load_from_env()
llm_gateway = LLMGateway(factory=ProviderFactory(), budget_manager=budget_manager)


def _contract_checker(request: MCPRequest) -> tuple[bool, Optional[str]]:
    if os.environ.get("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "1") == "0":
        return True, None
    if request.ferramenta in CONTRACT_EXEMPT_ACTIONS:
        return True, None
    try:
        outcome = contratos.verificar_detalhado(request.agente_id, request.ferramenta)
    except Exception:
        logger.exception("Contract verification failed")
        return False, "Falha interna na verificação de contrato (negado por padrão)"
    if outcome == VerificationOutcome.ALLOWED:
        request.metadata["contract_checked"] = True
        return True, None
    if outcome == VerificationOutcome.NO_CONTRACT:
        contratos.registrar_ausencia(request.agente_id, request.ferramenta, "Chamada MCP sem contrato ativo")
        return (
            False,
            "Nenhum contrato ativo autoriza esta ação para este agente. "
            "Use propose_contract/sign_contract primeiro.",
        )
    return False, f"Contrato ativo violado ({outcome}). Proponha um novo contrato antes de continuar."


def _contract_verifier(agente_id: str, acao: str) -> bool:
    outcome = contratos.verificar_detalhado(agente_id, acao)
    if outcome == VerificationOutcome.NO_CONTRACT:
        contratos.registrar_ausencia(agente_id, acao, "Ação entre agentes sem contrato ativo")
    return outcome == VerificationOutcome.ALLOWED


# RBAC allow-all is a deliberate, visible choice here: bridge authorization is
# enforced by contracts (_contract_checker) + qlipot risk + HITL, not by roles.
firewall = FirewallMCP(
    rbac_checker=permitir_tudo,
    hitl=hitl,
    contract_checker=_contract_checker,
    contract_verifier=_contract_verifier,
)
contratos.firewall = firewall
sync = SyncHub(qlipot=qlipot, contratos=contratos, firewall=firewall)
_retry_attempts: Dict[tuple[str, str, str], tuple[int, float]] = {}
MAX_RETRIES = 3
RETRY_WINDOW_SECONDS = 60


def _tool_annotations(
    title: str,
    *,
    read_only: bool,
    destructive: bool,
    idempotent: bool,
    open_world: bool,
) -> Dict[str, Any]:
    """Build MCP tool annotations with consistent Kabbalah policy hints."""
    return {
        "title": title,
        "readOnlyHint": read_only,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": open_world,
    }


class BridgeBaseInput(BaseModel):
    """Common metadata SillyTavern should pass for authorization context."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    agente_id: str = Field(default="sillytavern-agent", description="Stable agent identifier.")
    papel_agente: str = Field(default="blank-card-agent", description="Agent role/persona from SillyTavern.")
    intencao: Optional[str] = Field(default=None, description="Natural language intent for audit/risk evaluation.")


class ReadFileInput(BridgeBaseInput):
    """Input for read_file."""

    path: str = Field(..., description="Absolute or workspace-relative file path to read.", min_length=1)
    encoding: str = Field(default="utf-8", description="Text encoding used to read the file.")


class WriteFileInput(BridgeBaseInput):
    """Input for write_file."""

    path: str = Field(..., description="Absolute or workspace-relative file path to write.", min_length=1)
    content: str = Field(..., description="Text content to write.")
    encoding: str = Field(default="utf-8", description="Text encoding used to write the file.")


class ExecuteCommandInput(BridgeBaseInput):
    """Input for execute_command."""

    command: str = Field(..., description="Command line to execute after firewall/HITL approval.", min_length=1)
    cwd: Optional[str] = Field(default=None, description="Optional working directory.")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds.")


class NetworkRequestInput(BridgeBaseInput):
    """Input for network_request."""

    url: str = Field(..., description="URL to request.", min_length=1)
    method: str = Field(default="GET", description="HTTP method: GET, POST, PUT, PATCH, DELETE.")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers.")
    body: Optional[str] = Field(default=None, description="Optional request body.")
    timeout_seconds: int = Field(default=30, ge=1, le=120, description="HTTP timeout in seconds.")
    secret_item: Optional[str] = Field(default=None, description="Optional Bitwarden item name/ID.")
    secret_field: str = Field(default="api_key", description="Bitwarden field name to inject.")
    secret_header: str = Field(default="Authorization", description="Header name receiving the secret value.")
    secret_prefix: str = Field(default="Bearer ", description="Prefix before the secret in the header.")


class CompareModelsInput(BridgeBaseInput):
    """Input for compare_models."""

    task: str = Field(..., description="Task/prompt sent unchanged to each selected model.", min_length=1)
    providers: list[str] = Field(default_factory=list, description="Optional provider/profile names to compare.")
    role: str = Field(default="Leaf_Builder", description="Gateway role used for model selection.")
    capability: str = Field(default="chat", description="Required model capability.")
    max_tokens: int = Field(default=256, ge=1, le=4096, description="Maximum output tokens per provider.")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature per provider.")
    timeout_seconds: int = Field(default=30, ge=1, le=120, description="Per-provider timeout in seconds.")


class RenderGroupEventInput(BridgeBaseInput):
    """Input for render_group_event."""

    event_type: str = Field(..., description="allow, deny, hitl, budget, config, or error.", min_length=1)
    agent: str = Field(..., description="Visible SillyTavern group member/domain name.", min_length=1)
    summary: str = Field(..., description="Human-readable status summary.", min_length=1)
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details; secret-like keys are redacted.",
    )
    ticket_id: Optional[str] = Field(default=None, description="Optional HITL ticket ID.")
    next_step: Optional[str] = Field(default=None, description="Suggested next action.")


class ReadEnvVarInput(BridgeBaseInput):
    """Input for read_env_var."""

    name: str = Field(..., description="Environment variable name.", min_length=1)


class CallToolInput(BridgeBaseInput):
    """Input for cross-agent tool call authorization."""

    name: str = Field(..., description="Remote or delegated tool name.", min_length=1)
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the delegated tool.")
    target_agent: Optional[str] = Field(default=None, description="Provider/remote agent involved in the call.")


class DatabaseQueryInput(BridgeBaseInput):
    """Input for a local SQLite database query."""

    db_path: str = Field(..., description="SQLite database path.", min_length=1)
    query: str = Field(..., description="SQL query to execute.", min_length=1)
    parameters: list[Any] = Field(default_factory=list, description="Positional query parameters.")


class HITLStatusInput(BaseModel):
    """Input for HITL ticket status lookup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ticket_id: str = Field(..., description="HITL ticket ID returned by a blocked tool call.", min_length=1)


class ProposeContractInput(BridgeBaseInput):
    """Input for propose_contract."""

    agente_provedor: str = Field(..., min_length=1)
    acao: str = Field(..., min_length=1)
    limites: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    papeis: list[str] = Field(default_factory=lambda: ["viewer"])


class ContractIdInput(BridgeBaseInput):
    """Input for sign/reject contract operations."""

    contrato_id: str = Field(..., min_length=1)
    motivo: str = ""


class CompleteTaskInput(BridgeBaseInput):
    """Input for complete_task."""

    task_id: str = Field(..., min_length=1)


def _json_response(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _ok(result: Any, *, trace_id: str, decision: Any, intent: Any) -> str:
    return _json_response(
        {
            "ok": True,
            "trace_id": trace_id,
            "risk": {
                "score": decision.risk_score,
                "level": decision.risk_level.value,
                "reason": decision.motivo,
                "hitl_required": decision.hitl_required,
            },
            "intent": {
                "score_confianca": intent.score_confianca,
                "risco": intent.risco,
                "motivo": intent.motivo,
                "status": intent.status.value,
            },
            "result": result,
        }
    )


def _error(
    message: str,
    *,
    trace_id: str,
    code: str,
    details: Optional[Mapping[str, Any]] = None,
) -> str:
    return _json_response(
        {
            "ok": False,
            "trace_id": trace_id,
            "error": message,
            "code": code,
            "details": dict(details or {}),
        }
    )


def _hash_parametros(argumentos: Mapping[str, Any]) -> str:
    serialized = json.dumps(argumentos, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _allowed_dirs() -> list[Path]:
    raw = os.environ.get("KABBALAH_BRIDGE_ALLOWED_DIRS") or str(PROJECT_ROOT)
    parts = []
    for chunk in raw.split(os.pathsep):
        parts.extend(item for item in chunk.split(",") if item)
    return [Path(item).expanduser().resolve() for item in parts]


def _resolve_allowed_path(raw_path: str, *, must_exist: bool) -> Path:
    path = Path(raw_path).expanduser()
    if must_exist and not path.exists():
        raise BridgePolicyError(f"Caminho não existe: {raw_path}")
    resolved = path.resolve(strict=must_exist)
    for allowed in _allowed_dirs():
        if resolved == allowed or allowed in resolved.parents:
            return resolved
    raise BridgePolicyError(f"Caminho fora dos diretórios permitidos: {raw_path}")


def _env_allowlist() -> set[str]:
    raw = os.environ.get(
        "KABBALAH_BRIDGE_ENV_ALLOWLIST",
        "KABBALAH_PROVIDER,KABBALAH_PROVIDER_MODE,KABBALAH_MODEL,KABBALAH_LOG_LEVEL,PATH,HOME,LANG,TZ",
    )
    return {item.strip() for item in raw.split(",") if item.strip()}


def _assert_url_allowed(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise BridgePolicyError(f"Esquema de URL não permitido: {parsed.scheme}")
    if not parsed.hostname:
        raise BridgePolicyError("URL sem hostname válido")
    if os.environ.get("KABBALAH_BRIDGE_ALLOW_PRIVATE_NETWORKS") == "1":
        return
    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise BridgePolicyError(f"Falha ao resolver hostname: {parsed.hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise BridgePolicyError(f"Destino de rede bloqueado por política anti-SSRF: {ip}")


def _check_retry_limit(agente_id: str, ferramenta: str, argumentos: Mapping[str, Any]) -> Optional[str]:
    now = time.monotonic()
    key = (agente_id, ferramenta, _hash_parametros(argumentos))
    count, last_seen = _retry_attempts.get(key, (0, 0.0))
    if now - last_seen > RETRY_WINDOW_SECONDS:
        count = 0
    count += 1
    _retry_attempts[key] = (count, now)
    if count > MAX_RETRIES:
        return _json_response(
            {
                "ok": False,
                "error": "RETRY_LIMIT_EXCEEDED",
                "message": "Limite de tentativas excedido para esta ação. Aguarde 60s antes de repetir.",
                "details": {"max_retries": MAX_RETRIES, "window_seconds": RETRY_WINDOW_SECONDS},
            }
        )
    return None


def _hitl_required(
    *,
    trace_id: str,
    agente_id: str,
    acao: AcaoMCP,
    argumentos: Mapping[str, Any],
    decision: Any,
) -> str:
    ticket_id = f"hitl_{uuid.uuid4().hex[:12]}"
    hitl_decision = hitl.solicitar(
        agente_id=agente_id,
        acao=acao,
        risco=decision.risk_score,
        contexto={
            "argumentos": dict(argumentos),
            "motivo": decision.motivo,
            "risk_level": decision.risk_level.value,
        },
        trace_id=ticket_id,
        urgencia=NivelUrgencia.ALTA,
    )
    ticket_payload = {
        "ticket_id": ticket_id,
        "status": hitl_decision.status.value,
        "trace_id": trace_id,
        "agente_id": agente_id,
        "acao": acao.value,
        "argumentos": dict(argumentos),
        "risk_score": decision.risk_score,
        "risk_level": decision.risk_level.value,
        "motivo": hitl_decision.motivo,
    }
    tickets.put(ticket_id, ticket_payload)
    return _json_response(
        {
            "error": "HITL_REQUIRED",
            "ticket_id": ticket_id,
            "message": "Ação requer aprovação humana. Use o endpoint de consulta para verificar status.",
        }
    )


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _authorize_and_execute(
    *,
    acao: AcaoMCP,
    agente_id: str,
    papel_agente: str,
    argumentos: Dict[str, Any],
    executor: Callable[[], Any | Awaitable[Any]],
    intencao: Optional[str] = None,
    envolve_outro_agente: bool = False,
) -> str:
    """Run the mandatory qlipot -> firewall -> HITL/cofre -> execution pipeline."""

    trace_id = f"sillytavern:{uuid.uuid4()}"
    try:
        retry_error = _check_retry_limit(agente_id, acao.value, argumentos)
        if retry_error is not None:
            return retry_error

        intent = qlipot.avaliar_intencao(
            pedido=intencao or f"{acao.value} requested by {papel_agente}",
            ferramenta=acao.value,
            argumentos=argumentos,
            agente_id=agente_id,
        )
        if intent.bloqueado:
            return _error(
                "Acesso Bloqueado: Zona de Isolamento",
                trace_id=trace_id,
                code="QLIPOT_BLOCKED",
                details={
                    "motivo": intent.motivo,
                    "risco": intent.risco,
                    "score_confianca": intent.score_confianca,
                },
            )

        request = MCPRequest(
            agente_id=agente_id,
            ferramenta=acao.value,
            argumentos=argumentos,
            contrato_id="sillytavern-blank-card-bridge",
            trace_id=trace_id,
            metadata={
                "papel_agente": papel_agente,
                "risco": intent.risco,
                "score_confianca": intent.score_confianca,
                "intent_status": intent.status.value,
                "envolve_outro_agente": envolve_outro_agente,
            },
        )
        decision = firewall.autorizar(request)
        if not decision.autorizado:
            if decision.hitl_required:
                return _hitl_required(
                    trace_id=trace_id,
                    agente_id=agente_id,
                    acao=acao,
                    argumentos=argumentos,
                    decision=decision,
                )
            return _error(
                "Acesso Bloqueado: Zona de Isolamento",
                trace_id=trace_id,
                code="FIREWALL_DENIED",
                details={
                    "motivo": decision.motivo,
                    "risk_score": decision.risk_score,
                    "risk_level": decision.risk_level.value,
                    "hitl_required": decision.hitl_required,
                },
            )

        result = await _maybe_await(executor())
        qlipot.registrar_acao_agente(
            agente_id=agente_id,
            acao=acao.value,
            parametros={
                "argumentos": argumentos,
                "risk_score": decision.risk_score,
                "risk_level": decision.risk_level.value,
                "result_type": type(result).__name__,
            },
        )
        return _ok(result, trace_id=trace_id, decision=decision, intent=intent)
    except CofreError as exc:
        logger.exception("Cofre failure")
        return _error(
            "Cofre bloqueado ou indisponível",
            trace_id=trace_id,
            code="COFRE_ERROR",
            details={"error": str(exc)},
        )
    except BridgePolicyError as exc:
        logger.warning("Bridge policy denied request: %s", exc)
        return _error(str(exc), trace_id=trace_id, code="POLICY_DENIED")
    except Exception as exc:
        logger.exception("Bridge execution failure")
        return _error(
            "Erro interno no Kabbalah MCP Bridge",
            trace_id=trace_id,
            code="BRIDGE_ERROR",
            details={"error": str(exc)},
        )


@mcp.tool(
    name=AcaoMCP.READ_FILE.value,
    annotations=_tool_annotations(
        "Kabbalah Read File",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def read_file(params: ReadFileInput) -> str:
    """Read a text file only after qlipot, FirewallMCP, RBAC, and HITL checks."""

    def _execute() -> Dict[str, Any]:
        path = _resolve_allowed_path(params.path, must_exist=True)
        max_bytes = int(os.environ.get("KABBALAH_BRIDGE_MAX_READ_BYTES", "2097152"))
        if path.stat().st_size > max_bytes:
            raise BridgePolicyError(f"Arquivo excede limite de leitura de {max_bytes} bytes")
        content = path.read_text(encoding=params.encoding)
        return {"path": str(path), "content": content, "bytes": len(content.encode(params.encoding))}

    return await _authorize_and_execute(
        acao=AcaoMCP.READ_FILE,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.WRITE_FILE.value,
    annotations=_tool_annotations(
        "Kabbalah Write File",
        read_only=False,
        destructive=True,
        idempotent=False,
        open_world=False,
    ),
)
async def write_file(params: WriteFileInput) -> str:
    """Write a text file only after Kabbalah authorization."""

    def _execute() -> Dict[str, Any]:
        path = _resolve_allowed_path(params.path, must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(params.content, encoding=params.encoding)
        return {"path": str(path), "bytes": len(params.content.encode(params.encoding))}

    return await _authorize_and_execute(
        acao=AcaoMCP.WRITE_FILE,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.EXECUTE_COMMAND.value,
    annotations=_tool_annotations(
        "Kabbalah Execute Command",
        read_only=False,
        destructive=True,
        idempotent=False,
        open_world=False,
    ),
)
async def execute_command(params: ExecuteCommandInput) -> str:
    """Execute a local command only after qlipot, FirewallMCP, RBAC, and HITL checks."""

    def _execute() -> Dict[str, Any]:
        if os.environ.get("KABBALAH_BRIDGE_ENABLE_SHELL") != "1":
            raise BridgePolicyError("execute_command requer KABBALAH_BRIDGE_ENABLE_SHELL=1")
        cwd = str(_resolve_allowed_path(params.cwd, must_exist=True)) if params.cwd else None
        completed = subprocess.run(
            params.command,
            shell=True,
            cwd=cwd,
            timeout=params.timeout_seconds,
            capture_output=True,
            text=True,
        )
        return {
            "command": params.command,
            "cwd": params.cwd,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return await _authorize_and_execute(
        acao=AcaoMCP.EXECUTE_COMMAND,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.READ_ENV_VAR.value,
    annotations=_tool_annotations(
        "Kabbalah Read Env Var",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def read_env_var(params: ReadEnvVarInput) -> str:
    """Read a non-sensitive environment variable after authorization."""

    def _execute() -> Dict[str, Any]:
        if params.name not in _env_allowlist():
            return {
                "name": params.name,
                "blocked": True,
                "reason": "ENV_NOT_ALLOWLISTED",
                "hint": "Adicione a variável em KABBALAH_BRIDGE_ENV_ALLOWLIST se ela puder ser exposta.",
            }
        return {"name": params.name, "value": os.environ.get(params.name)}

    return await _authorize_and_execute(
        acao=AcaoMCP.READ_ENV_VAR,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.CALL_TOOL.value,
    annotations=_tool_annotations(
        "Kabbalah Call Tool",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=True,
    ),
)
async def call_tool(params: CallToolInput) -> str:
    """Authorize a cross-agent/delegated tool call without bypassing contracts."""

    def _execute() -> Dict[str, Any]:
        return {"name": params.name, "target_agent": params.target_agent, "args": params.args, "authorized": True}

    return await _authorize_and_execute(
        acao=AcaoMCP.CALL_TOOL,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=_execute,
        envolve_outro_agente=True,
    )


@mcp.tool(
    name=AcaoMCP.DATABASE_QUERY.value,
    annotations=_tool_annotations(
        "Kabbalah Database Query",
        read_only=False,
        destructive=True,
        idempotent=False,
        open_world=False,
    ),
)
async def database_query(params: DatabaseQueryInput) -> str:
    """Execute a local SQLite query after Kabbalah authorization."""

    def _execute() -> Dict[str, Any]:
        db_path = _resolve_allowed_path(params.db_path, must_exist=True)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(params.query, params.parameters)
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {"rows": rows, "rowcount": len(rows)}
            conn.commit()
            return {"rows": [], "rowcount": cursor.rowcount}

    return await _authorize_and_execute(
        acao=AcaoMCP.DATABASE_QUERY,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.NETWORK_REQUEST.value,
    annotations=_tool_annotations(
        "Kabbalah Network Request",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=True,
    ),
)
async def network_request(params: NetworkRequestInput) -> str:
    """Perform an HTTP request after Kabbalah authorization and optional vault lookup."""

    def _execute() -> Dict[str, Any]:
        _assert_url_allowed(params.url)
        headers = dict(params.headers)
        if params.secret_item:
            secret = cofre.get_chave(params.secret_item, field_name=params.secret_field)
            headers[params.secret_header] = f"{params.secret_prefix}{secret}"

        response = requests.request(
            method=params.method.upper(),
            url=params.url,
            headers=headers,
            data=params.body,
            timeout=params.timeout_seconds,
            allow_redirects=False,
        )
        return {
            "url": params.url,
            "method": params.method.upper(),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
        }

    return await _authorize_and_execute(
        acao=AcaoMCP.NETWORK_REQUEST,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(exclude={"secret_item", "secret_field"}),
        executor=lambda: asyncio.to_thread(_execute),
    )


@mcp.tool(
    name=AcaoMCP.CHECK_HITL_STATUS.value,
    annotations=_tool_annotations(
        "Kabbalah HITL Status",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def check_hitl_status(params: HITLStatusInput) -> str:
    """Return the current status of a pending HITL ticket."""

    ticket = await asyncio.to_thread(tickets.get, params.ticket_id)
    if ticket is None:
        return _json_response(
            {
                "ok": False,
                "error": "HITL_TICKET_NOT_FOUND",
                "ticket_id": params.ticket_id,
                "message": "Ticket HITL não encontrado.",
            }
        )
    return _json_response({"ok": True, **ticket})


hitl_status = check_hitl_status


@mcp.tool(
    name=AcaoMCP.PROPOSE_CONTRACT.value,
    annotations=_tool_annotations(
        "Kabbalah Propose Contract",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=False,
    ),
)
async def propose_contract(params: ProposeContractInput) -> str:
    """Propose an agent contract. Only coordinator roles are allowed."""

    def _execute() -> Dict[str, Any]:
        contrato = contratos.propor(
            requisitante=params.agente_id,
            provedor=params.agente_provedor,
            acao=params.acao,
            limites=params.limites,
            papeis=params.papeis,
            task_id=params.task_id,
        )
        return contrato.__dict__

    return await _authorize_and_execute(
        acao=AcaoMCP.PROPOSE_CONTRACT,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=_execute,
    )


@mcp.tool(
    name=AcaoMCP.SIGN_CONTRACT.value,
    annotations=_tool_annotations(
        "Kabbalah Sign Contract",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=False,
    ),
)
async def sign_contract(params: ContractIdInput) -> str:
    """Sign a proposed agent contract as the provider."""

    return await _authorize_and_execute(
        acao=AcaoMCP.SIGN_CONTRACT,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: {
            "signed": contratos.assinar(params.contrato_id, params.agente_id),
            "contrato_id": params.contrato_id,
        },
    )


@mcp.tool(
    name=AcaoMCP.REJECT_CONTRACT.value,
    annotations=_tool_annotations(
        "Kabbalah Reject Contract",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=False,
    ),
)
async def reject_contract(params: ContractIdInput) -> str:
    """Reject a proposed agent contract as the provider."""

    return await _authorize_and_execute(
        acao=AcaoMCP.REJECT_CONTRACT,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: {
            "rejected": contratos.rejeitar(params.contrato_id, params.agente_id, params.motivo),
            "contrato_id": params.contrato_id,
        },
    )


@mcp.tool(
    name=AcaoMCP.COMPLETE_TASK.value,
    annotations=_tool_annotations(
        "Kabbalah Complete Task",
        read_only=False,
        destructive=False,
        idempotent=False,
        open_world=False,
    ),
)
async def complete_task(params: CompleteTaskInput) -> str:
    """Mark a task complete and close all associated contracts."""

    def _execute() -> Dict[str, Any]:
        completed = contratos.complete_task(params.task_id, params.agente_id)
        return {"task_id": params.task_id, "completed_contracts": [contrato.__dict__ for contrato in completed]}

    return await _authorize_and_execute(
        acao=AcaoMCP.COMPLETE_TASK,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=_execute,
    )


@mcp.tool(
    name=AcaoMCP.GET_NETWORK_STATS.value,
    annotations=_tool_annotations(
        "Kabbalah Network Stats",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def get_network_stats(params: BridgeBaseInput) -> str:
    """Return Sync Hub local network statistics."""

    return await _authorize_and_execute(
        acao=AcaoMCP.GET_NETWORK_STATS,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: sync.get_network_stats(),
    )


@mcp.tool(
    name=AcaoMCP.GET_BUDGET_STATS.value,
    annotations=_tool_annotations(
        "Kabbalah Budget Stats",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def get_budget_stats(params: BridgeBaseInput) -> str:
    """Return local LLM budget and consumption statistics."""

    return await _authorize_and_execute(
        acao=AcaoMCP.GET_BUDGET_STATS,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: budget_manager.get_budget_stats(),
    )


@mcp.tool(
    name=AcaoMCP.COMPARE_MODELS.value,
    annotations=_tool_annotations(
        "Kabbalah Compare Models",
        read_only=True,
        destructive=False,
        idempotent=False,
        open_world=True,
    ),
)
async def compare_models(params: CompareModelsInput) -> str:
    """Run the same task through selected LLM providers and return comparison rows."""

    auth_args = params.model_dump()
    auth_args["output_limit"] = auth_args.pop("max_tokens")

    return await _authorize_and_execute(
        acao=AcaoMCP.COMPARE_MODELS,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao or params.task,
        argumentos=auth_args,
        executor=lambda: compare_model_outputs(
            task=params.task,
            gateway=llm_gateway,
            providers=params.providers,
            role=params.role,
            capability=params.capability,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
            timeout=float(params.timeout_seconds),
            trace_id=f"{params.agente_id}:compare_models",
        ),
    )


@mcp.tool(
    name=AcaoMCP.RENDER_GROUP_EVENT.value,
    annotations=_tool_annotations(
        "Kabbalah Render Group Event",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def render_group_event(params: RenderGroupEventInput) -> str:
    """Render a Kabbalah status event for a SillyTavern group chat."""

    return await _authorize_and_execute(
        acao=AcaoMCP.RENDER_GROUP_EVENT,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao or params.summary,
        argumentos=params.model_dump(),
        executor=lambda: render_group_chat_event(
            event_type=params.event_type,
            agent=params.agent,
            summary=params.summary,
            details=params.details,
            ticket_id=params.ticket_id,
            next_step=params.next_step,
        ),
    )


@mcp.tool(
    name=AcaoMCP.GET_CONFIG_STATUS.value,
    annotations=_tool_annotations(
        "Kabbalah Config Status",
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
)
async def get_config_status(params: BridgeBaseInput) -> str:
    """Return safe installation configuration status without secret values."""

    return await _authorize_and_execute(
        acao=AcaoMCP.GET_CONFIG_STATUS,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=lambda: config_manager.get_config_status(),
    )


if __name__ == "__main__":
    mcp.run()
