"""Tests for human-in-the-loop approval gates."""

from kabbalah.hitl import HITL, ApprovalRequest, ApprovalStatus


def test_hitl_approval_records_audit_entry():
    hitl = HITL(approval_provider=lambda request: True)
    request = ApprovalRequest(
        agente_id="agent-1",
        acao="executar_mcp",
        risco=0.72,
        contexto={"ferramenta": "filesystem.write"},
        trace_id="trace-1",
    )

    decision = hitl.solicitar_aprovacao(request)

    assert decision.aprovado is True
    assert decision.status == ApprovalStatus.APPROVED
    assert decision.trace_id == "trace-1"
    assert hitl.audit_log[-1].status == ApprovalStatus.APPROVED


def test_hitl_denial_records_audit_entry():
    hitl = HITL(approval_provider=lambda request: False)
    request = ApprovalRequest(
        agente_id="agent-1",
        acao="executar_mcp",
        risco=0.91,
        contexto={},
        trace_id="trace-2",
    )

    decision = hitl.solicitar_aprovacao(request)

    assert decision.aprovado is False
    assert decision.status == ApprovalStatus.DENIED
    assert hitl.audit_log[-1].trace_id == "trace-2"


def test_hitl_requires_explicit_provider_for_non_interactive_runtime():
    hitl = HITL()
    request = ApprovalRequest(
        agente_id="agent-1",
        acao="executar_mcp",
        risco=0.8,
        contexto={},
        trace_id="trace-3",
    )

    decision = hitl.solicitar_aprovacao(request)

    assert decision.aprovado is False
    assert decision.status == ApprovalStatus.PENDING
    assert "approval provider" in decision.motivo.lower()
