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
import inspect
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from kabbalah.cofre import CofreBitwarden, CofreError
from kabbalah.firewall_mcp import AcaoMCP, FirewallMCP, MCPRequest
from kabbalah.hitl import HITL, NivelUrgencia
from kabbalah.qlipot import Qlipot

logging.basicConfig(
    level=os.environ.get("KABBALAH_LOG_LEVEL", "WARNING").upper(),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("kabbalah_mcp_bridge")

mcp = FastMCP("kabbalah_mcp")

hitl = HITL()
cofre = CofreBitwarden(use_cache=True)
qlipot = Qlipot()
firewall = FirewallMCP(hitl=hitl)
_hitl_tickets: Dict[str, Dict[str, Any]] = {}


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


class HITLStatusInput(BaseModel):
    """Input for HITL ticket status lookup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ticket_id: str = Field(..., description="HITL ticket ID returned by a blocked tool call.", min_length=1)


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
    _hitl_tickets[ticket_id] = {
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
) -> str:
    """Run the mandatory qlipot -> firewall -> HITL/cofre -> execution pipeline."""

    trace_id = f"sillytavern:{uuid.uuid4()}"
    try:
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
        return _error("Cofre bloqueado ou indisponível", trace_id=trace_id, code="COFRE_ERROR", details={"error": str(exc)})
    except Exception as exc:
        logger.exception("Bridge execution failure")
        return _error("Erro interno no Kabbalah MCP Bridge", trace_id=trace_id, code="BRIDGE_ERROR", details={"error": str(exc)})


@mcp.tool(
    name=AcaoMCP.READ_FILE.value,
    annotations={"title": "Kabbalah Read File", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def read_file(params: ReadFileInput) -> str:
    """Read a text file only after qlipot, FirewallMCP, RBAC, and HITL checks."""

    def _execute() -> Dict[str, Any]:
        path = Path(params.path).expanduser()
        content = path.read_text(encoding=params.encoding)
        return {"path": str(path), "content": content, "bytes": len(content.encode(params.encoding))}

    return await _authorize_and_execute(
        acao=AcaoMCP.READ_FILE,
        agente_id=params.agente_id,
        papel_agente=params.papel_agente,
        intencao=params.intencao,
        argumentos=params.model_dump(),
        executor=_execute,
    )


@mcp.tool(
    name=AcaoMCP.EXECUTE_COMMAND.value,
    annotations={"title": "Kabbalah Execute Command", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
)
async def execute_command(params: ExecuteCommandInput) -> str:
    """Execute a local command only after qlipot, FirewallMCP, RBAC, and HITL checks."""

    def _execute() -> Dict[str, Any]:
        completed = subprocess.run(
            params.command,
            shell=True,
            cwd=params.cwd,
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
        executor=_execute,
    )


@mcp.tool(
    name=AcaoMCP.NETWORK_REQUEST.value,
    annotations={"title": "Kabbalah Network Request", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def network_request(params: NetworkRequestInput) -> str:
    """Perform an HTTP request after Kabbalah authorization and optional vault lookup."""

    def _execute() -> Dict[str, Any]:
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
    name="hitl_status",
    annotations={"title": "Kabbalah HITL Status", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def hitl_status(params: HITLStatusInput) -> str:
    """Return the current status of a pending HITL ticket."""

    ticket = _hitl_tickets.get(params.ticket_id)
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


if __name__ == "__main__":
    mcp.run()
