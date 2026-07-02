# Kabbalah Agent Contracts and Sync Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o bridge SillyTavern/Kabbalah com contratos entre agentes, Sync Hub federado, limite de retries e ferramentas MCP adicionais.

**Architecture:** Preservar as APIs já existentes e adicionar a nova camada de contratos/sinapses como extensão compatível. O bridge continua sendo o ponto único de interceptação MCP; firewall, qlipot, hitl, contratos e sync hub expõem APIs pequenas e testáveis.

**Tech Stack:** Python 3.11, FastMCP, Pydantic, pytest, módulos locais `src/kabbalah`.

---

### Task 1: Sync Hub federado

**Files:**
- Modify: `src/kabbalah/sync_hub.py`
- Test: `tests/test_sync_hub.py`

- [ ] Adicionar dataclasses `Sinapse` e `ReputacaoInstancia`.
- [ ] Manter `SyncUpdate`, `registrar_update()` e `agregar()` para compatibilidade.
- [ ] Implementar fila de sinapses, quarentena, ban list, hash de hardware, internalização com 3 confirmações e `get_network_stats()`.
- [ ] Testar coleta, quarentena, internalização e banimento.

### Task 2: Contratos entre agentes

**Files:**
- Modify: `src/kabbalah/contratos.py`
- Test: `tests/test_agent_contracts.py`

- [ ] Manter `ContratoSucesso` para compatibilidade.
- [ ] Adicionar `ContratoAgente` e serviço `Contratos`.
- [ ] Implementar `propor`, `assinar`, `rejeitar`, `verificar`, `registrar_violacao`, `complete_task`, `revogar`, `contratos_por_task`.
- [ ] Testar RBAC coordinator, ativação, limites, conclusão, rejeição, revogação e callback de violação.

### Task 3: Integração qlipot, hitl e firewall

**Files:**
- Modify: `src/kabbalah/qlipot.py`
- Modify: `src/kabbalah/hitl.py`
- Modify: `src/kabbalah/firewall_mcp.py`
- Test: `tests/test_sillytavern_mcp_bridge.py`, `tests/test_firewall_mcp.py`

- [ ] Adicionar callbacks e `aplicar_correcao()` em qlipot.
- [ ] Adicionar regra temporal de 3 scores recentes acima de 0.40.
- [ ] Adicionar `revogar_contrato()` em HITL.
- [ ] Expandir `AcaoMCP` com ferramentas e contratos.
- [ ] Adicionar `verificar_contrato()` e callback de bloqueio no firewall.

### Task 4: Bridge MCP

**Files:**
- Modify: `kabbalah_mcp_bridge.py`
- Modify/Create: `sillytavern_config.json`
- Test: `tests/test_sillytavern_mcp_bridge.py`

- [ ] Instanciar `Contratos` e `SyncHub`.
- [ ] Adicionar retry guard por `(agente_id, ferramenta, hash_parametros)` com `max_retries=3` e janela de 60s.
- [ ] Adicionar ferramentas `write_file`, `read_env_var`, `call_tool`, `database_query`, `check_hitl_status`, `propose_contract`, `sign_contract`, `reject_contract`, `complete_task`, `get_network_stats`.
- [ ] Garantir logs somente em stderr e respostas JSON sem segredos.

### Task 5: Validação e publicação

**Files:**
- All touched files.

- [ ] Rodar testes focalizados.
- [ ] Rodar suíte completa.
- [ ] Rodar scan de segredos.
- [ ] Commitar e publicar em `origin/main`.
