# Kabbalah — Plano de Execução para IA Executora (Handoff)

> **Gerado por**: Claude Fable 5, 2026-07-04, após implementar as ondas 1–3 de hardening.
> **Executor alvo**: outra IA de codificação (qualquer uma), sob direção de Charles Nóbrega.
> **Fontes**: análise externa `MELHORIAS_E_APRIMORAMENTOS.md` (raiz do repo) **reconciliada com verificação direta do código em 2026-07-04**. Onde este documento e a análise externa divergirem, **este documento vence** — cada achado aqui foi verificado com grep/leitura no código atual.
> **Idioma**: docs em português; código, docstrings e mensagens de commit em inglês; nomes de domínio (classes/métodos do kernel) permanecem em português (`Contratos`, `Qlipot`, `verificar_detalhado`).

---

## 0. ESTADO REAL DO REPOSITÓRIO (verificado em 2026-07-04)

- **Branch atual**: `hardening/wave-2` (commits `f48568b` wave-2 e `69c7850` wave-3, sobre `c1cdfba`). Não mergeado em `main` — decisão de merge é do Charles (ver §6).
- **Suíte de testes**: `1127 passed, 89 skipped` (skips = testes live de providers, desligados por política — **é o estado esperado, não conserte**). O número "812/74 failed" citado na análise externa é de um snapshot de abril/2026 — **obsoleto**.
- **Ondas de hardening 1–3 completas** (ver `docs/roadmap/hardening-next-waves.md`):
  - Onda 1: bridge MCP + ToolExecutionEngine (contratos obrigatórios, shell opt-in, SSRF, allowlists).
  - Onda 2: contratos persistentes em SQLite (`src/kabbalah/contrato_store.py`), `max_calls` atômico, log de violações append-only, separação ausência×violação (`VerificationOutcome`).
  - Onda 3: normalização unicode (NFKC, zero-width, homoglyphs), padrões regex de comandos destrutivos, decodificação base64 no scoring, sinônimos pt/en, `aplicar_correcao` com origem autorizada + clamp ±0.30 + auditoria, `RISK_ASSESSOR_VERSION`; Cofre com `BITWARDEN_CLI_PATH`, `KABBALAH_BW_SHA256`, `clear_on_read`, `limpar_cache()`.

### Reconciliação com `MELHORIAS_E_APRIMORAMENTOS.md`

| Item | Status verificado hoje |
|---|---|
| M4 (bypass case/unicode) | ✅ Feito na onda 3 — manter testes, evoluir só via M11 |
| M7 (contratos SQLite + race) | ✅ Feito na onda 2 |
| `aplicar_correcao` sem auth (Parte 3.1) | ✅ Feito na onda 3 |
| Cofre PATH/cache (Parte 3.4) | ✅ Feito na onda 3 |
| M1 (LeafNode mudo) | ❌ Pendente — `src/kabbalah/domain_orchestrator.py:215` ainda retorna placeholder |
| M3 (LLMGateway órfão) | ❌ Pendente — zero imports externos a `llm_gateway.py` em `src/` |
| M5 (RBAC `_allow_all`) | ❌ Pendente — `src/kabbalah/firewall_mcp.py:85` e defaults na linha 127–128 |
| M6 (enforcement sem log) | ❌ Pendente — `fsm_enforcement.py:162` (sem log) vs `:180` (com log) |
| M16 (MockProvider exportado) | ❌ Pendente — `src/kabbalah/providers/__init__.py:14,27` |
| M13 (`openclaude/`) | ❌ Pendente — diretório existe na raiz, não é importado por nada |
| M14 (CLI) | ⚠️ Reduzido — `src/kabbalah/cli.py` EXISTE com `main()`; falta só validar |
| M15 (README mente) | ⚠️ Reduzido — README atual já é honesto (6 providers, sem claim de produção). Resta arquivar ~43 relatórios `.md`/`.txt` da raiz |
| M2 (fallback memória) | ⚠️ Verificar antes de agir (ver Onda 5.3) |
| M8, M9, M12, M17, M18 | ❌ Pendentes (features novas) |
| M10, M11 | ⏸️ Bloqueados por decisão humana (ver §6) |

### APIs reais da camada de providers (verificadas)

- `ProviderFactory` — `src/kabbalah/providers/factory.py:37`; `create_provider(...)` linha 66; `get_provider_for_role(role) -> BaseProvider` linha 172; `get_provider_stats(name)` linha 216.
- `BaseProvider.execute_request(...)` — `src/kabbalah/providers/base.py:61`. Stats: `total_cost` acumulado em `base.py:57,165`, lido apenas em `get_stats()` (`:152-153`) — ninguém consome (insumo do M12).
- `MockProvider` — gated por `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`; é a ferramenta correta para testes e2e sem chamadas live.
- `LLMGateway` / `selecionar_provider` — `src/kabbalah/llm_gateway.py`, órfão (nenhum import externo).
- Banco de estado: `KABBALAH_BRIDGE_STATE_DB` (default `.kabbalah_bridge_state.sqlite3`), tabelas `hitl_tickets`, `contratos`, `contrato_eventos`. **Use `src/kabbalah/contrato_store.py` como implementação de referência para qualquer novo store SQLite** (lock + conexão por operação + busy_timeout + append-only para auditoria).

---

## 1. ARQUITETURA ALVO

### 1.1 Visão em camadas

```
                     ┌──────────────────────────────────────┐
  ENTRADA            │  SillyTavern / CLI / MCP clients      │
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
  KERNEL DE          │  kabbalah_mcp_bridge.py (stdio MCP)   │
  SEGURANÇA          │   1. Qlipot.avaliar_intencao          │
  (pipeline pré-     │   2. FirewallMCP.autorizar            │
   execução —        │      RBAC (deny-by-default, Onda 6)   │
   NUNCA enfraquecer)│      + Contratos.verificar_detalhado  │
                     │      + risk score                     │
                     │   3. HITL (fail-safe: pendente≠aprovado)│
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
  ORQUESTRAÇÃO       │  RootOrchestrator → DomainOrchestrator│
                     │  → LeafNode (Onda 5 conecta ao LLM)   │
                     │  AutonomyLoop → tree search (Onda 9)  │
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
  CAMADA LLM         │  LLMGateway (seletor canônico: role,  │
  (Onda 5)           │   custo, budget) ← ÚNICO ponto de     │
                     │   decisão de provider                 │
                     │  └→ ProviderFactory (constrói)        │
                     │     └→ OpenAI/Gemini/Groq/Mistral/    │
                     │        Together/DeepSeek/Mock(gated)  │
                     │  BudgetManager (Onda 7) intercepta AQUI│
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
  PERSISTÊNCIA       │  SQLite único (KABBALAH_BRIDGE_STATE_DB)│
  E AUDITORIA        │  hitl_tickets · contratos ·           │
                     │  contrato_eventos (append-only) ·     │
                     │  budget_ledger (Onda 7, append-only)  │
                     └──────────────────────────────────────┘
```

### 1.2 Decisões arquiteturais canônicas (não rediscutir, implementar)

1. **`LLMGateway` é o seletor de topo; `ProviderFactory` é o construtor.** LeafNode e qualquer consumidor de LLM falam SÓ com o gateway. A factory nunca é chamada diretamente fora do gateway (exceto em testes).
2. **Fail-closed em tudo**: exceção em verificação = negado; ausência de configuração = negado (após Onda 6); HITL sem provider de aprovação = pendente, nunca auto-aprovado.
3. **Auditoria é append-only**: novos stores de auditoria seguem `contrato_eventos` (sem API de update/delete).
4. **Nada de mock em runtime** (`docs/specs/NO_MOCK_RUNTIME_POLICY.md`): `MockProvider` só sob `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`, e só em testes.
5. **Código importável só em `src/kabbalah/`**. Nunca criar módulos runtime na raiz.
6. **Um banco de estado** para o bridge; cada subsistema tem suas tabelas, nunca um arquivo SQLite próprio por módulo.

---

## 2. REGRAS PARA A IA EXECUTORA

Ambiente: Windows 11, PowerShell, Python 3.11 no venv do repo.

```powershell
cd E:\projetos\kabbalah
.venv\Scripts\python.exe -m pytest tests -q          # suíte completa (~2.5 min)
.venv\Scripts\python.exe -m pytest tests/test_X.py -q # direcionado (rode PRIMEIRO)
```

1. **Antes de qualquer onda**: rode a suíte completa. Baseline esperado: 1127+ passed, 89 skipped, 0 failed. Se houver failures ANTES de você mexer, PARE e reporte — não "conserte de passagem".
2. **Cada item concluído = 1 commit** com mensagem convencional em inglês (`feat:`, `fix:`, `security:`, `chore:`, `docs:`) descrevendo o quê e por quê. O hook de pre-commit verifica segredos — se falhar, investigue; **nunca use `--no-verify`**.
3. **Nunca faça `git push`** sem pedido explícito do Charles.
4. **Uma branch por onda**: `wave-4-hygiene`, `wave-5-llm-loop`, etc., criada a partir da branch base que o Charles indicar (hoje: `hardening/wave-2`).
5. **Ao concluir cada item, marque o checkbox neste arquivo** e atualize `README.md` se o comportamento visível mudou. Este doc é a fonte de verdade do progresso.
6. **Testes primeiro nos arquivos afetados, depois suíte completa.** Todo item novo exige testes novos (padrão do repo: pytest + Hypothesis para propriedades; veja `tests/test_contrato_store.py` como referência de estilo).
7. **Não confie nos ~43 relatórios `.md`/`.txt` da raiz** (`PHASE*_COMPLETE`, `FINAL_*`, `PROJECT_*`): contêm claims falsos de "produção aprovada". Serão arquivados na Onda 4. A verdade operacional está em: `README.md`, `docs/roadmap/*`, `docs/audit/FORENSIC_AUDIT_2026-04-11.md` e no código.
8. **Não toque**: `.env` (real, do usuário), `.venv/`, `.hypothesis/`, testes skipped de providers live, `openclaude/` exceto para removê-lo na Onda 4.
9. **Nunca enfraqueça um default de segurança** para fazer um teste passar. Se um teste existente conflitar com um endurecimento pedido aqui, atualize o teste e documente a mudança de comportamento no commit (precedente: onda 3 mudou `read_env_var` de `BW_PASSWORD` para HITL — commit `69c7850`).
10. Se algo divergir do descrito aqui (arquivo movido, assinatura diferente), **verifique com grep antes de improvisar** e registre a divergência no commit.

---

## 3. ONDAS DE EXECUÇÃO

Ordem obrigatória: 4 → 5 → 6 → 7. Depois, 8 e 9 podem intercalar. Onda 10 só com aprovação humana.

---

### ONDA 4 — Higiene do repositório (M13+M15+M16+M14) — esforço: ~2 dias

> **⚠️ SUBSTITUÍDA por especificação detalhada**: execute
> [cleanup-execution-plan.md](cleanup-execution-plan.md), que expande esta onda com
> inventário verificado (duplicatas, código órfão, consolidação de docs em um único
> `docs/ARCHITECTURE.md`, higiene de git e checklist pré-GitHub). Os itens 4.1–4.4
> abaixo estão contidos nele — ficam aqui só como resumo.

Objetivo: repo honesto e navegável. Baixo risco, serve de calibração do executor.

- [ ] **4.1 (M13) Remover `openclaude/`** — é um clone Git completo de projeto TypeScript, não integrado (zero imports; confirme com `grep -rn "openclaude" src/ tests/ kabbalah_mcp_bridge.py setup.py` — deve retornar nada relevante antes de remover). `git rm -r openclaude/` + entrada no `.gitignore` se necessário.
  *Aceite*: diretório fora do working tree; suíte verde; `pip install -e .` funciona.
- [ ] **4.2 (M15) Arquivar relatórios da raiz** — mover os ~43 `.md`/`.txt` de status/fase da raiz para `docs/archive/reports/` (plano já previsto em `docs/architecture/REPOSITORY_STRUCTURE.md`). **Permanecem na raiz**: `README.md`, `LICENSE`, `CONTRIBUTING.md`, `MELHORIAS_E_APRIMORAMENTOS.md` (análise atual, não é relatório falso), `SECURITY_ALERT.md`/`SECURITY_MIGRATION.md` (avalie: se ainda relevantes, mover para `docs/`; senão, arquivar), e arquivos de configuração (`setup.py`, `pytest.ini`, `requirements*.txt`, `sillytavern*.json`).
  *Aceite*: raiz com ≤ 15 arquivos; nenhum link quebrado no README; suíte verde.
- [ ] **4.3 (M16) Tirar `MockProvider` do export público** — remover `MockProvider`/`MockResponseType` de `__all__` em `src/kabbalah/providers/__init__.py` (linhas 14 e 27). Manter o arquivo. Ajustar imports de testes para `from kabbalah.providers.mock_provider import MockProvider`.
  *Aceite*: `from kabbalah.providers import MockProvider` falha; testes ajustados; suíte verde.
- [ ] **4.4 (M14) Validar a CLI** — `src/kabbalah/cli.py` existe com `main()`. Valide: `.venv\Scripts\python.exe -m kabbalah.cli --help` e o entrypoint `kabbalah` (`setup.py:47-48`). Verifique se a CLI passa pelos gates do kernel (não deve haver caminho que execute ações sem Qlipot/Firewall). Corrija problemas pequenos; se a CLI estiver fundamentalmente quebrada, reporte em vez de reescrever.
  *Aceite*: `--help` funciona com exit code 0; comandos documentados no README.

---

### ONDA 5 — Fechar o loop LLM (M1+M3+M2) — esforço: 3-5 dias — **A ONDA MAIS IMPORTANTE**

Objetivo: input → orquestração → provider real → artifact, com o kernel no meio. Sem isso o projeto é um motor sem correia.

- [ ] **5.1 (M3) Gateway canônico** — fazer de `LLMGateway` o único seletor:
  1. Leia `src/kabbalah/llm_gateway.py` inteiro e `src/kabbalah/providers/factory.py:37-230`.
  2. Refatore o gateway para: `selecionar_provider(role: str, *, budget_hint: float | None = None) -> BaseProvider`, decidindo por role (delegando a `ProviderFactory.get_provider_for_role`, `factory.py:172`) e preparado para custo (M12 injeta o budget depois).
  3. O gateway é construído com uma `ProviderFactory` injetada (testável com MockProvider gated).
  *Aceite*: testes unitários do gateway (seleção por role, erro claro para role desconhecido); nenhum consumidor chama `ProviderFactory` diretamente fora do gateway e de testes.
- [ ] **5.2 (M1) Conectar o LeafNode** — implementar `_execute_leaf_node` em `src/kabbalah/domain_orchestrator.py:215`:
  1. `DomainOrchestrator` recebe (injeção opcional no construtor) um `LLMGateway`. Sem gateway injetado → comportamento atual de placeholder MAS com `status="skipped"` e metadata explicando (nunca mais `success` vazio — é mentira de status).
  2. Com gateway: montar prompt do leaf a partir de `leaf_node.description` + contexto do domain; chamar `provider.execute_request(...)` (assinatura real em `base.py:61` — leia antes); empacotar `ProviderResponse.content` como artifact; registrar em metadata: provider usado, tokens, custo, latência.
  3. Erro de provider → `LeafResult(status="failure", ...)` com o erro em metadata — exceção não pode derrubar a árvore inteira (o AutonomyLoop trata replanning).
  4. Teste e2e: com `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1` e MockProvider via gateway, rodar Root→Domain→Leaf e verificar artifact real no resultado. Teste do caminho sem gateway (status skipped). Teste do caminho de erro.
  *Aceite*: e2e verde com mock gated; `status="success"` só com artifact real; suíte completa verde.
- [ ] **5.3 (M2) Fallback de memória** — **primeiro verifique** (a claim é da análise externa): induza a ausência de Cognee e rode os testes de memória. Se `ensure_consistency()` de fato falhar sem Cognee (`src/kabbalah/memory_subsystem.py`), separe a consistência por backend: backend opcional ausente = degradação com warning, nunca exceção que envenene o JSONL saudável. Se a claim não se reproduzir, marque este item como "não se reproduz" e siga.
  *Aceite*: suíte verde com e sem Cognee instalado; Qlipot continua funcional (scoring temporal usa essa memória).

---

### ONDA 6 — Segurança residual (M5+M6) — esforço: 1-2 dias

- [ ] **6.1 (M5) RBAC deny-by-default** — em `src/kabbalah/firewall_mcp.py`:
  1. Linhas 85 e 127: o default de `rbac_checker` é `_allow_all`. Trocar por `_deny_all` (motivo claro: "Nenhum rbac_checker configurado — negado por padrão (fail-closed)").
  2. **Atenção**: linha 128 também aplica `_allow_all` a `contract_checker` — avaliar caso a caso: o bridge injeta os dois; para uso como biblioteca, contract_checker sem injeção também deve negar (consistência fail-closed).
  3. Escape hatch temporário e explícito: construtor aceita `rbac_checker=permitir_tudo` importável (`from kabbalah.firewall_mcp import permitir_tudo`) — a permissividade tem que ser opt-in visível no código do chamador, nunca default.
  4. Corrigir os testes que constroem `FirewallMCP()` puro (vão passar a ser negados — atualize-os para injetar `permitir_tudo` quando o teste não for sobre RBAC).
  *Aceite*: `FirewallMCP()` sem checkers nega tudo; bridge continua funcionando (já injeta); commit documenta a mudança de default.
- [ ] **6.2 (M6) Log no enforcement principal** — em `src/kabbalah/fsm_enforcement.py`: `check_operation_allowed` (linha 162) não loga; `check_operation_allowed_with_logging` (linha 180) loga. Unificar: a variante principal SEMPRE loga bloqueios; `_with_logging` vira alias deprecated (manter por compat, com `DeprecationWarning`).
  *Aceite*: teste provando que um BLOCK pelo caminho principal gera registro de auditoria; grep confirma que nenhum caller depende da variante sem log para silêncio.

---

### ONDA 7 — Budget Manager (M12) — esforço: 2-3 dias — depende da Onda 5

Objetivo: custo passa a ser controlado, não só acumulado. Insumo: `total_cost` já é acumulado por provider (`base.py:57,165`) e exposto em `get_stats()` — falta quem leia e haja.

- [ ] **7.1** Criar `src/kabbalah/budget_manager.py`: `BudgetLedger` (SQLite, tabela `budget_ledger` append-only no mesmo state DB — siga o padrão de `contrato_store.py`) registrando cada chamada (provider, model, tokens, custo, trace_id, timestamp) + `BudgetManager` com limites configuráveis (por run, por dia, por provider) via env `KABBALAH_BUDGET_*`.
- [ ] **7.2** Integração: o **LLMGateway consulta o BudgetManager antes de retornar provider**; estourou → exceção clara `BudgetExceededError` (modo `block`) ou warning logado (modo `warn`). **Default: `warn`** na primeira release; `block` via `KABBALAH_BUDGET_MODE=block`.
- [ ] **7.3** Expor `get_budget_stats` como tool no bridge (mesmo padrão de `get_network_stats`).
  *Aceite*: teste de limite estourado nos dois modos; ledger append-only (sem API de update/delete); leaf registra custo no ledger a cada execução; suíte verde.

---

### ONDA 8 — Features visíveis (M8+M9) — esforço: 5-8 dias — depende das Ondas 5 e 7

- [ ] **8.1 (M8) Model Comparison** — nova tool `compare_models` no bridge: mesma task despachada a N providers (via gateway, respeitando budget), retorna tabela JSON: provider, latência, tokens, custo, resposta. Passa pelo pipeline de segurança normal (contrato + firewall + qlipot) como qualquer tool. Sem API keys live configuradas → erro honesto por provider, não mock.
  *Aceite*: teste com MockProvider gated simulando 2 "providers"; entrada documentada no README.
- [ ] **8.2 (M9) Group Chat SillyTavern** — mapear orquestração para sala ST: cada domain = um bot; decisões do Firewall/HITL aparecem como mensagens. Item mais aberto — **produza primeiro um design doc curto** (`docs/specs/st-group-chat-design.md`) com o mapeamento proposto e critérios, e só então implemente. Se o esforço explodir (>5 dias), pare no design doc e reporte.

---

### ONDA 9 — Fronteira de pesquisa (M17+M18) — esforço: 3-6 semanas — depende das Ondas 5 e 7

- [ ] **9.1 (M17) Kabbalah-Bench** — benchmark de contenção (inspirado no CoffeeBench da Sakana, foco ataque/defesa):
  1. `benchmarks/` novo (fora de `src/`), com cenários red-team declarativos (YAML/JSON): agente tenta `rm -rf`, exfiltração via base64, escalada de privilégio, encadeamento de tools, sinônimos/homoglyphs (reaproveite os vetores dos testes da onda 3).
  2. Harness que roda cada cenário contra o pipeline real (Qlipot→Firewall→HITL com MockProvider gated) e mede: taxa de bloqueio correto, taxa de falso-positivo (cenários benignos de controle são obrigatórios), latência de decisão, overhead.
  3. Saída: relatório JSON + markdown em `benchmarks/results/` (datado, nunca sobrescrever — histórico é o valor).
  *Aceite*: `python -m benchmarks.run` executa ponta a ponta; baseline registrado; documentado no README como medir.
- [ ] **9.2 (M18) AutonomyLoop → Tree Search com budget** — evoluir `src/kabbalah/autonomy_loop.py` (replanning linear) para busca: gerar M ramos, pontuar resultados dos leafs, podar abaixo de threshold, aprofundar promissores, orçamento por ramo vindo do BudgetManager (M12). **Design doc primeiro** (`docs/specs/tree-search-design.md`: algoritmo, scoring, critério de poda, interação com HITL — um ramo bloqueado por HITL é podado ou pausado?). Implementar incrementalmente com o loop linear preservado como fallback (`KABBALAH_SEARCH_MODE=linear|tree`, default `linear` até validado).
  *Aceite*: property tests (budget nunca excedido; poda determinística dado score); e2e com mock; benchmark M17 rodado antes/depois para comparar contenção.

---

### ONDA 10 — Bloqueada por decisão humana (M10+M11) — **NÃO INICIAR sem aprovação do Charles**

- [ ] **10.1 (M10) Sandbox real** — requer decisão de infra: E2B (cloud, pago) vs Firecracker/gVisor (self-hosted, Linux — atenção: dev atual é Windows). Até lá, o mitigador é a onda 1 (shell desligado por default no bridge).
- [ ] **10.2 (M11) Classificador ML no Qlipot** — requer decisão de modelo (Llama Prompt Guard ou treinado), dataset e infra de avaliação. O M17 (bench) deve existir ANTES, para medir se o ML supera as heurísticas da onda 3.

---

## 4. O QUE NÃO FAZER (para qualquer onda)

- Não recriar o que as ondas 1–3 já fizeram (cheque a tabela de reconciliação em §0).
- Não ativar providers live nem gravar API keys em lugar algum.
- Não "consertar" os 89 skips.
- Não fazer push, não usar `--no-verify`, não commitar `.env`.
- Não adicionar dependências pesadas sem registrar razão no commit (e prefira `requirements-*.txt` opcionais, padrão do repo).
- Não converter o repo para inglês total nem para português total — a convenção mista é intencional.
- Não confiar em nenhum documento da raiz exceto `README.md` e `MELHORIAS_E_APRIMORAMENTOS.md`; a verdade está em `docs/` e no código.

## 5. DEFINIÇÃO DE PRONTO (por onda)

1. Todos os checkboxes da onda marcados neste arquivo.
2. Suíte completa: 0 failed (passed pode crescer; 89 skipped constantes).
3. Um commit por item, hook de segredos verde.
4. README/docs atualizados se comportamento visível mudou.
5. Divergências encontradas registradas neste doc (seção nova "Divergências" ao final, se necessário).

## 6. DECISÕES PENDENTES DO CHARLES (gates)

| # | Decisão | Bloqueia |
|---|---|---|
| 1 | Mergear `hardening/wave-2` em `main` antes de começar? (recomendado: sim) | Todas as ondas |
| 2 | E2B (pago/cloud) vs Firecracker (self-hosted/Linux) | Onda 10.1 |
| 3 | Modelo ML para o Qlipot + orçamento de avaliação | Onda 10.2 |
| 4 | API keys live para smoke test real do loop LLM (opcional; mock cobre o essencial) | Qualidade extra da Onda 5 |
