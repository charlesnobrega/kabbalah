import os

from kabbalah.contratos import Contratos
from kabbalah.firewall_mcp import AcaoMCP, FirewallMCP, MCPRequest, permitir_tudo
from kabbalah.hitl import HITL
from kabbalah.qlipot import Qlipot


CONTRACT_EXEMPT_ACTIONS = {
    "propose_contract",
    "sign_contract",
    "reject_contract",
    "complete_task",
    "check_hitl_status",
    "get_network_stats",
}


def make_firewall():
    hitl = HITL()
    qlipot = Qlipot()
    contratos = Contratos(qlipot=qlipot, hitl=hitl)

    def contract_checker(request: MCPRequest):
        if os.environ.get("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", "1") == "0":
            return True, None
        if request.ferramenta in CONTRACT_EXEMPT_ACTIONS:
            return True, None
        if contratos.verificar(request.agente_id, request.ferramenta):
            return True, None
        return False, "Nenhum contrato ativo autoriza esta ação para este agente. Use propose_contract/sign_contract primeiro."

    firewall = FirewallMCP(
        rbac_checker=permitir_tudo,
        hitl=hitl,
        contract_checker=contract_checker,
        contract_verifier=contratos.verificar,
    )
    return firewall, contratos


def request_for(agent: str, action: str) -> MCPRequest:
    return MCPRequest(
        agente_id=agent,
        ferramenta=action,
        argumentos={},
        contrato_id="bridge",
        trace_id=f"trace-{agent}-{action}",
        metadata={"risco": 0.1},
    )


def test_contract_gate_full_lifecycle(monkeypatch):
    monkeypatch.delenv("KABBALAH_BRIDGE_REQUIRE_CONTRACTS", raising=False)
    firewall, contratos = make_firewall()

    no_contract = firewall.autorizar(request_for("agent-a", AcaoMCP.READ_FILE.value))
    assert no_contract.autorizado is False

    exempt = firewall.autorizar(request_for("agent-a", AcaoMCP.PROPOSE_CONTRACT.value))
    assert exempt.autorizado is True

    contrato = contratos.propor(
        requisitante="coordinator",
        provedor="agent-a",
        acao=AcaoMCP.READ_FILE.value,
        limites={"max_calls": 5},
        papeis=["coordinator"],
    )
    assert contratos.assinar(contrato.id, "agent-a") is True

    for _ in range(5):
        assert firewall.autorizar(request_for("agent-a", AcaoMCP.READ_FILE.value)).autorizado is True

    sixth = firewall.autorizar(request_for("agent-a", AcaoMCP.READ_FILE.value))
    assert sixth.autorizado is False

    other_agent = firewall.autorizar(request_for("agent-b", AcaoMCP.READ_FILE.value))
    assert other_agent.autorizado is False
