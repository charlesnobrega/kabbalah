import importlib
import json
from pathlib import Path

import pytest

from kabbalah.firewall_mcp import AcaoMCP, MCPDecision, MCPRequest, MCPRiskLevel
from kabbalah.qlipot import IntentEvaluation, QlipotStatus


def reload_bridge(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KABBALAH_BRIDGE_ALLOWED_DIRS", str(tmp_path))
    monkeypatch.setenv("KABBALAH_BRIDGE_STATE_DB", str(tmp_path / "bridge_state.sqlite3"))
    import kabbalah_mcp_bridge as bridge

    return importlib.reload(bridge)


def test_contract_checker_fails_closed_without_active_contract(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)
    request = MCPRequest(
        agente_id="agent-without-contract",
        ferramenta=AcaoMCP.READ_FILE.value,
        argumentos={},
        contrato_id="bridge",
        trace_id="trace",
        metadata={},
    )

    allowed, reason = bridge._contract_checker(request)

    assert allowed is False
    assert "Nenhum contrato ativo" in reason


def test_contract_checker_exempts_contract_bootstrap_tools(monkeypatch, tmp_path):
    bridge = reload_bridge(monkeypatch, tmp_path)
    request = MCPRequest(
        agente_id="agent-without-contract",
        ferramenta=AcaoMCP.PROPOSE_CONTRACT.value,
        argumentos={},
        contrato_id="bridge",
        trace_id="trace",
        metadata={},
    )

    assert bridge._contract_checker(request) == (True, None)


@pytest.mark.asyncio
async def test_read_env_var_blocks_not_allowlisted_env(monkeypatch, tmp_path):
    monkeypatch.setenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "0")
    bridge = reload_bridge(monkeypatch, tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgres://must-not-leak")

    response = await bridge.read_env_var(
        bridge.ReadEnvVarInput(agente_id="agent", papel_agente="viewer", name="DATABASE_URL")
    )
    payload = json.loads(response)

    assert payload["result"]["blocked"] is True
    assert payload["result"]["reason"] == "ENV_NOT_ALLOWLISTED"
    assert "postgres" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_execute_command_requires_shell_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "0")
    bridge = reload_bridge(monkeypatch, tmp_path)
    monkeypatch.delenv("KABBALAH_BRIDGE_ENABLE_SHELL", raising=False)
    monkeypatch.setattr(
        bridge.firewall,
        "autorizar",
        lambda request: MCPDecision(
            autorizado=True,
            motivo="authorized",
            trace_id=request.trace_id,
            agente_id=request.agente_id,
            ferramenta=request.ferramenta,
            risk_level=MCPRiskLevel.LOW,
            risk_score=0.1,
        ),
    )

    response = await bridge.execute_command(
        bridge.ExecuteCommandInput(agente_id="agent", papel_agente="operator", command="echo blocked")
    )
    payload = json.loads(response)

    assert payload["code"] == "POLICY_DENIED"
    assert "KABBALAH_BRIDGE_ENABLE_SHELL" in payload["error"]


@pytest.mark.asyncio
async def test_read_file_denies_path_outside_allowed_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "0")
    bridge = reload_bridge(monkeypatch, tmp_path)

    response = await bridge.read_file(
        bridge.ReadFileInput(agente_id="agent", papel_agente="reader", path=str(tmp_path.parent / "outside.txt"))
    )
    payload = json.loads(response)

    assert payload["code"] == "POLICY_DENIED"


@pytest.mark.asyncio
async def test_hitl_ticket_persists_in_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "0")
    bridge = reload_bridge(monkeypatch, tmp_path)
    ticket_id = "hitl_test_ticket"
    payload = {"ticket_id": ticket_id, "status": "pending"}

    await bridge.asyncio.to_thread(bridge.tickets.put, ticket_id, payload)
    response = await bridge.check_hitl_status(bridge.HITLStatusInput(ticket_id=ticket_id))

    assert json.loads(response)["status"] == "pending"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost:8080",
        "http://169.254.169.254/latest/meta-data",
        "ftp://x/",
    ],
)
def test_network_policy_blocks_ssrf_and_non_http(monkeypatch, tmp_path, url):
    bridge = reload_bridge(monkeypatch, tmp_path)

    with pytest.raises(bridge.BridgePolicyError):
        bridge._assert_url_allowed(url)


@pytest.mark.asyncio
async def test_read_file_enforces_max_read_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "0")
    monkeypatch.setenv("KABBALAH_BRIDGE_MAX_READ_BYTES", "4")
    bridge = reload_bridge(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge.qlipot,
        "avaliar_intencao",
        lambda **_: IntentEvaluation(
            score_confianca=0.9,
            risco=0.1,
            bloqueado=False,
            motivo="test",
            status=QlipotStatus.RECUPERADO,
            score_atual=0.1,
            score_contexto=0.0,
            score_final=0.1,
        ),
    )
    path = tmp_path / "large.txt"
    path.write_text("12345", encoding="utf-8")

    response = await bridge.read_file(
        bridge.ReadFileInput(agente_id="max-read-agent", papel_agente="reader", path=str(path))
    )
    payload = json.loads(response)

    assert payload["code"] == "POLICY_DENIED"
