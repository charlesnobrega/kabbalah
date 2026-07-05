# Kabbalah — Plano de Execução para IA Executora (Handoff)

> **Gerado por**: Claude Fable 5, 2026-07-04, após implementar as ondas 1–3 de hardening.
> **Executor alvo**: outra IA de codificação (qualquer uma), sob direção de Charles Nóbrega.
> **Fontes**: análise externa `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md` **reconciliada com verificação direta do código em 2026-07-04**. Onde este documento e a análise externa divergirem, **este documento vence** — cada achado aqui foi verificado com grep/leitura no código atual.
> **Idioma**: docs em português; código, docstrings e mensagens de commit em inglês; nomes de domínio (classes/métodos do kernel) permanecem em português (`Contratos`, `Qlipot`, `verificar_detalhado`).

---

## 0. ESTADO REAL DO REPOSITÓRIO (verificado em 2026-07-04)

- **Branch atual**: `main` pós-merge das ondas anteriores; Onda 7 continuada nesta branch em 2026-07-04.
- **Branches históricas de execução**: `wave-4-hygiene` e `wave-5-llm-loop`, criadas em 2026-07-04 e já reconciliadas neste handoff.
- **Suíte de testes**: `1185 passed, 89 skipped` em 2026-07-04 na branch `main` com `.venv\Scripts\python.exe -m pytest tests -q` (skips = testes live de providers, desligados por política — **é o estado esperado, não conserte**). O número "812/74 failed" citado na análise externa é de um snapshot de abril/2026 — **obsoleto**.
- **Ondas de hardening 1–3 completas** (ver `docs/roadmap/hardening-next-waves.md`):
  - Onda 1: bridge MCP + ToolExecutionEngine (contratos obrigatórios, shell opt-in, SSRF, allowlists).
  - Onda 2: contratos persistentes em SQLite (`src/kabbalah/contrato_store.py`), `max_calls` atômico, log de violações append-only, separação ausência×violação (`VerificationOutcome`).
  - Onda 3: normalização unicode (NFKC, zero-width, homoglyphs), padrões regex de comandos destrutivos, decodificação base64 no scoring, sinônimos pt/en, `aplicar_correcao` com origem autorizada + clamp ±0.30 + auditoria, `RISK_ASSESSOR_VERSION`; Cofre com `BITWARDEN_CLI_PATH`, `KABBALAH_BW_SHA256`, `clear_on_read`, `limpar_cache()`.

### Reconciliação com `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md`

| Item | Status verificado hoje |
|---|---|
| M4 (bypass case/unicode) | ✅ Feito na onda 3 — manter testes, evoluir só via M11 |
| M7 (contratos SQLite + race) | ✅ Feito na onda 2 |
| `aplicar_correcao` sem auth (Parte 3.1) | ✅ Feito na onda 3 |
| Cofre PATH/cache (Parte 3.4) | ✅ Feito na onda 3 |
| M1 (LeafNode mudo) | ✅ Feito na onda 5 — `DomainOrchestrator` executa leaf via `LLMGateway` injetado; sem gateway retorna `status="skipped"` explícito |
| M3 (LLMGateway órfão) | ✅ Feito na onda 5 — gateway virou seletor canônico por role/capability/budget e é consumido pelo leaf via injeção |
| M5 (RBAC `_allow_all`) | ✅ Feito na onda 6 — `FirewallMCP` nega por padrão sem checkers; permissividade só via `permitir_tudo` explícito (bridge injeta com comentário) |
| M6 (enforcement sem log) | ✅ Feito na onda 6 — `check_operation_allowed` sempre loga bloqueios; `_with_logging` é alias deprecated sem double-log |
| M16 (MockProvider exportado) | ✅ Feito na onda 4 — `MockProvider`/`MockResponseType` ficam em `kabbalah.providers.mock_provider`, não em `kabbalah.providers` |
| M13 (`openclaude/`) | ✅ Feito na onda 4 — diretório local removido após confirmar zero referências |
| M14 (CLI) | ✅ Feito na onda 4 — `python -m kabbalah.cli --help` e entrypoint `kabbalah --help` exit 0 |
| M15 (README/relatórios) | ✅ Feito na onda 4 — README atualizado, links validados, relatórios raiz arquivados/removidos quando duplicados |
| M2 (fallback memória) | ✅ Verificado na onda 5 — com `cognee_present=False`, memória JSONL + Qlipot passaram testes direcionados |
| M12 (Budget Manager) | ✅ Feito na onda 7 — limites por run/dia/provider, modos `warn|block`, gateway enforcement, tool `get_budget_stats`, fallback de providers e custos reais no ledger |
| M8, M9, M17, M18 | ❌ Pendentes (features novas) |
| M10, M11 | ⏸️ Bloqueados por decisão humana (ver §6) |

### APIs reais da camada de providers (verificadas)

- `ProviderFactory` — `src/kabbalah/providers/factory.py`; constrói providers nativos e OpenAI-compatible, incluindo `ollama_local`, `openrouter`, `groq_compatible`, `cerebras` e `sambanova`.
- `BaseProvider.execute_request(...)` — `src/kabbalah/providers/base.py`. Stats: `total_cost` segue disponível em `get_stats()`; chamadas de leaf também gravam consumo no `BudgetLedger` quando injetado.
- `MockProvider` — gated por `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`; é a ferramenta correta para testes e2e sem chamadas live.
- `LLMGateway` / `CapabilityRegistry` — `src/kabbalah/llm_gateway.py`, seletor canônico por `role`, `capability` e `budget_hint`.
- `BudgetLedger` / `BudgetManager` — `src/kabbalah/budget_manager.py`, ledger SQLite append-only e enforcement configurável por `KABBALAH_BUDGET_*`.
- `HardwareProfiler` — `src/kabbalah/hardware_profile.py`, perfil local com fingerprint, fit/tier de modelos locais e tabela `hardware_profiles`.
- Banco de estado: `KABBALAH_BRIDGE_STATE_DB` (default `.kabbalah_bridge_state.sqlite3`), tabelas `hitl_tickets`, `contratos`, `contrato_eventos`, `budget_ledger` e `hardware_profiles`. **Use `src/kabbalah/contrato_store.py` como implementação de referência para qualquer novo store SQLite** (lock + conexão por operação + busy_timeout + append-only para auditoria).

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
                     │  → LeafNode via LLMGateway injetado   │
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
                     │  HardwareProfiler classifica fit local │
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
  PERSISTÊNCIA       │  SQLite único (KABBALAH_BRIDGE_STATE_DB)│
  E AUDITORIA        │  hitl_tickets · contratos ·           │
                     │  contrato_eventos (append-only) ·     │
                     │  budget_ledger · hardware_profiles    │
                     └──────────────────────────────────────┘
```

### 1.2 Decisões arquiteturais canônicas (não rediscutir, implementar)

1. **`LLMGateway` é o seletor de topo; `ProviderFactory` é o construtor.** LeafNode e qualquer consumidor de LLM falam SÓ com o gateway. A factory nunca é chamada diretamente fora do gateway (exceto em testes).
2. **Fail-closed em tudo**: exceção em verificação = negado; ausência de configuração = negado (após Onda 6); HITL sem provider de aprovação = pendente, nunca auto-aprovado.
3. **Auditoria é append-only**: novos stores de auditoria seguem `contrato_eventos` (sem API de update/delete).
4. **Nada de mock em runtime** (`docs/specs/NO_MOCK_RUNTIME_POLICY.md`): `MockProvider` só sob `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`, e só em testes.
5. **Código importável só em `src/kabbalah/`**. Nunca criar módulos runtime na raiz.
6. **Um banco de estado** para o bridge; cada subsistema tem suas tabelas, nunca um arquivo SQLite próprio por módulo.
7. **Fronteira provider × tool**: o que *raciocina* (texto → texto/estrutura) é
   provider e entra pelo LLMGateway; o que *gera artefato ou executa ação*
   (áudio, música, imagem, vídeo, e-mail, comandos) é **tool** e entra pelo
   pipeline MCP/execution engine com governança por ação. Ex.: ElevenLabs e
   ComfyUI são tools, nunca providers. Serviços sem API oficial (ex.: Suno) só
   entram via MCP server de terceiro, como tool externa governada — **nunca**
   embutir scraper/engenharia reversa no kernel.
8. **Compatibilidade por medição, não por marca**: suporte a GPU/hardware é
   herdado do runtime local (Ollama/llama.cpp — CUDA/ROCm/Metal/Vulkan/CPU);
   o Kabbalah detecta e **mede** (tokens/s), nunca presume por vendor. Perfis
   de hardware são eventos auditáveis. Workflows de mídia (ComfyUI) são
   tratados como código: allowlist de templates, agente só injeta parâmetros.

---

## 2. REGRAS PARA A IA EXECUTORA

Ambiente: Windows 11, PowerShell, Python 3.11 no venv do repo.

```powershell
cd E:\projetos\kabbalah
.venv\Scripts\python.exe -m pytest tests -q          # suíte completa (~2.5 min)
.venv\Scripts\python.exe -m pytest tests/test_X.py -q # direcionado (rode PRIMEIRO)
```

1. **Antes de qualquer onda**: rode a suíte completa. Baseline esperado: 1169+ passed, 89 skipped, 0 failed. Se houver failures ANTES de você mexer, PARE e reporte — não "conserte de passagem".
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

Ordem: as ondas 4 (limpeza) e 5 (loop LLM) são independentes — podem ser executadas
em qualquer ordem, conforme prioridade do Charles. Depois delas: 6 → 7; 8 e 9 podem
intercalar. A Fase A do plano de limpeza (scan de segredos no histórico) é obrigatória
antes de qualquer push ao GitHub, independente da ordem. Onda 10 só com aprovação humana.

---

### ONDA 4 — Higiene do repositório (M13+M15+M16+M14) — ✅ concluída em 2026-07-04

> **⚠️ SUBSTITUÍDA por especificação detalhada**: execute
> [cleanup-execution-plan.md](cleanup-execution-plan.md), que expande esta onda com
> inventário verificado (duplicatas, código órfão, consolidação de docs em um único
> `docs/ARCHITECTURE.md`, higiene de git e checklist pré-GitHub). Os itens 4.1–4.4
> abaixo estão contidos nele — ficam aqui só como resumo.

Objetivo: repo honesto e navegável. Baixo risco, serve de calibração do executor.

- [x] **4.1 (M13) Remover `openclaude/`** — é um clone Git completo de projeto TypeScript, não integrado (zero imports; confirme com `grep -rn "openclaude" src/ tests/ kabbalah_mcp_bridge.py setup.py` — deve retornar nada relevante antes de remover). `git rm -r openclaude/` + entrada no `.gitignore` se necessário.
  *Aceite*: diretório fora do working tree; suíte verde; `pip install -e .` funciona.
- [x] **4.2 (M15) Arquivar relatórios da raiz** — mover os ~43 `.md`/`.txt` de status/fase da raiz para `docs/archive/reports/` (plano já previsto em `docs/ARCHITECTURE.md`). **Permanecem na raiz**: `README.md`, `LICENSE`, `CONTRIBUTING.md`, arquivos de configuração (`setup.py`, `pytest.ini`, `requirements*.txt`, `sillytavern*.json`) e entradas operacionais (`kabbalah_mcp_bridge.py`, `.env.example`, `.gitignore`, `.gitattributes`, `ruff.toml`).
  *Aceite*: raiz com ≤ 15 arquivos; nenhum link quebrado no README; suíte verde.
- [x] **4.3 (M16) Tirar `MockProvider` do export público** — remover `MockProvider`/`MockResponseType` de `__all__` em `src/kabbalah/providers/__init__.py` (linhas 14 e 27). Manter o arquivo. Ajustar imports de testes para `from kabbalah.providers.mock_provider import MockProvider`.
  *Aceite*: `from kabbalah.providers import MockProvider` falha; testes ajustados; suíte verde.
- [x] **4.4 (M14) Validar a CLI** — `src/kabbalah/cli.py` existe com `main()`. Valide: `.venv\Scripts\python.exe -m kabbalah.cli --help` e o entrypoint `kabbalah` (`setup.py:47-48`). Verifique se a CLI passa pelos gates do kernel (não deve haver caminho que execute ações sem Qlipot/Firewall). Corrija problemas pequenos; se a CLI estiver fundamentalmente quebrada, reporte em vez de reescrever.
  *Aceite*: `--help` funciona com exit code 0; comandos documentados no README.

---

### ONDA 5 — Fechar o loop LLM (M1+M3+M2 + capacidades + hardware) — esforço: 5-8 dias — **A ONDA MAIS IMPORTANTE**

Objetivo: input → orquestração → provider real → artifact, com o kernel no meio,
medindo consumo desde a primeira chamada e adaptado ao hardware da máquina.
Decisões de design fechadas com o Charles em 2026-07-04 — implementar, não rediscutir.

**Sobre chaves**: o Charles preenche o `.env` local (gitignorado) a partir do cofre
pessoal dele. O executor referencia SÓ nomes de variáveis de ambiente, nunca lê o
cofre, nunca escreve valor de chave em código, teste, log ou commit.

- [x] **5.1 (M3) Gateway canônico + registro de capacidades** — fazer de `LLMGateway` o único seletor:
  1. Leia `src/kabbalah/llm_gateway.py` inteiro e `src/kabbalah/providers/factory.py:37-230`.
  2. Crie o **registro de capacidades**: cada modelo registrado declara
     `capabilities` (ex.: `chat`, `code`, `reasoning`), `context_window`,
     `custo_por_1m_tokens` (entrada/saída), `licenca` (`paga|open|agregador`),
     `local|cloud`, e para locais: `backend` (`cuda|rocm|metal|vulkan|cpu`),
     `quant` (ex.: `q4_K_M`, `qat-int4`), `min_vram_full`, `min_vram_offload`,
     `max_context_no_perfil`, `tokens_s_medido` (preenchido pelo 5.5).
  3. Gateway seleciona por `(role, capability, budget_hint)` com política
     **cheap-first com escalada**: tier local → rápido/barato → premium; escala
     quando o role exige ou quando a validação do contrato de sucesso falha.
  4. Construído com `ProviderFactory` injetada (testável com MockProvider gated).
  *Aceite*: testes de seleção por role e por capability; erro claro para
  role/capability desconhecidos; nenhum consumidor chama a factory diretamente.
- [x] **5.2 Adaptador genérico OpenAI-compatible** — uma classe
  `OpenAICompatibleProvider(base_url, api_key_env, model)` cobre a maioria dos
  fornecedores (o protocolo da OpenAI é o padrão de facto). Registrar na factory
  com estas entradas iniciais (nomes de env — valores são do Charles):
  | Entrada | base_url | env da chave | Tier |
  |---|---|---|---|
  | Ollama local | `http://localhost:11434/v1` | (sem chave) | local |
  | OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | agregador universal |
  | Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | rápido/barato |
  | Cerebras | `https://api.cerebras.ai/v1` | `CEREBRAS_API_KEY` | rápido/barato |
  | SambaNova | `https://api.sambanova.ai/v1` | `SAMBANOVA_API_KEY` | rápido/barato |
  Notas: DeepSeek e modelos Anthropic/Claude entram **via OpenRouter** (decisão
  do Charles — não criar providers diretos para eles). Os providers nativos
  existentes (OpenAI, Gemini, Mistral) permanecem como tier premium.
  **Chave ausente = provider indisponível no registro** (sem crash, sem pedir
  segredo no meio de execução): o gateway simplesmente não oferece o tier e o
  erro/log instrui a rodar `kabbalah setup` (item 8.0). Este `.env` é só o
  bootstrap de desenvolvimento do executor — o fluxo do usuário final é o 8.0.
  `LocalLLMProvider` legado: substituir pelo adaptador genérico apontando para o
  endpoint OpenAI-compat do Ollama; não manter dois caminhos para o mesmo destino.
  *Aceite*: teste do adaptador contra servidor HTTP fake; entrada Ollama
  selecionável pelo gateway; base_urls/env configuráveis sem tocar código.
- [x] **5.3 (M1) Conectar o LeafNode** — implementar `_execute_leaf_node` em `src/kabbalah/domain_orchestrator.py:215`:
  1. `DomainOrchestrator` recebe (injeção opcional no construtor) um `LLMGateway`. Sem gateway injetado → comportamento atual de placeholder MAS com `status="skipped"` e metadata explicando (nunca mais `success` vazio — é mentira de status).
  2. Com gateway: montar prompt do leaf a partir de `leaf_node.description` + contexto do domain; chamar `provider.execute_request(...)` (assinatura real em `base.py:61` — leia antes); empacotar `ProviderResponse.content` como artifact; registrar em metadata: provider usado, tokens, custo, latência.
  3. Erro de provider → `LeafResult(status="failure", ...)` com o erro em metadata — exceção não pode derrubar a árvore inteira (o AutonomyLoop trata replanning).
  4. Teste e2e: com `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1` e MockProvider via gateway, rodar Root→Domain→Leaf e verificar artifact real no resultado. Teste do caminho sem gateway (status skipped). Teste do caminho de erro.
  *Aceite*: e2e verde com mock gated; `status="success"` só com artifact real; suíte completa verde.
- [x] **5.4 Ledger de consumo desde a primeira chamada** — criar já a tabela
  `budget_ledger` (append-only, mesmo state DB, padrão `contrato_store.py`) em
  modo **só-registro** (sem limites — a Onda 7 adiciona enforcement em cima):
  provider, model, tokens de entrada/saída, custo, trace_id, timestamp. Tokens
  vêm do campo `usage` reportado pelo provider na resposta — **nunca** estimar
  por `len/4` (estimativa só para streaming em andamento, marcada como estimada).
  Toda execução de leaf grava uma linha.
  *Aceite*: e2e do 5.3 gera linhas no ledger; tabela sem API de update/delete.
- [x] **5.5 HardwareProfiler** — `src/kabbalah/hardware_profile.py`:
  1. **Detecção em 3 degraus**: API do vendor (NVML para NVIDIA; amdsmi/Level
     Zero se presentes) → fallback neutro (enumeração Vulkan e/ou WMI
     `Win32_VideoController` no Windows) → perfil CPU-only (psutil: núcleos,
     RAM, flags AVX). Nunca falhar por hardware desconhecido — degradar.
  2. **Fingerprint** = hash de (GPU modelo+VRAM total, vendor, backend
     disponível, CPU modelo, RAM total). Boot: fingerprint igual → carrega
     perfil salvo (partida ~ms). Diferente (upgrade OU downgrade) →
     **re-baseline**: recalcula fit estático de cada modelo local do registro
     (cabe inteiro / roda com offload / não roda) e roda micro-benchmark
     opcional (N tokens no menor modelo local → `tokens_s_medido`).
  3. **Tiers por medição, não por marca**: `interativo` / `batch` /
     `indisponivel` derivados de tokens/s medidos — nada de regra por vendor.
  4. Persistir em tabela `hardware_profiles` (append-only — mudança de hardware
     é evento auditável). Unificar com o `hardware_hash` do SyncHub: o profiler
     vira a fonte canônica desse hash.
  5. Guarda de runtime (VRAM livre antes do dispatch + feedback de OOM) fica
     para a Onda 7/8 — registrar TODO no código, não implementar agora.
  *Aceite*: perfil gerado em máquina só-CPU (CI) e com GPU; mudança simulada de
  fingerprint dispara re-baseline; registro reflete o fit; suíte verde.
- [x] **5.6 (M2) Fallback de memória** — **primeiro verifique** (a claim é da análise externa): induza a ausência de Cognee e rode os testes de memória. Se `ensure_consistency()` de fato falhar sem Cognee (`src/kabbalah/memory_subsystem.py`), separe a consistência por backend: backend opcional ausente = degradação com warning, nunca exceção que envenene o JSONL saudável. Se a claim não se reproduzir, marque este item como "não se reproduz" e siga.
  *Aceite*: suíte verde com e sem Cognee instalado; Qlipot continua funcional (scoring temporal usa essa memória).
  *Resultado 2026-07-04*: claim não se reproduziu com `cognee_present=False`;
  `tests/test_memory_subsystem.py`, `tests/test_memory_subsystem_properties.py`
  e `tests/test_qlipot_hardening_wave3.py` passaram via `.venv`.

---

### ONDA 6 — Segurança residual (M5+M6) — esforço: 1-2 dias

- [x] **6.1 (M5) RBAC deny-by-default** *(Claude, 2026-07-04 — testes em `tests/test_hardening_wave6.py`; suíte 1156 passed/89 skipped)* — em `src/kabbalah/firewall_mcp.py`:
  1. Linhas 85 e 127: o default de `rbac_checker` é `_allow_all`. Trocar por `_deny_all` (motivo claro: "Nenhum rbac_checker configurado — negado por padrão (fail-closed)").
  2. **Atenção**: linha 128 também aplica `_allow_all` a `contract_checker` — avaliar caso a caso: o bridge injeta os dois; para uso como biblioteca, contract_checker sem injeção também deve negar (consistência fail-closed).
  3. Escape hatch temporário e explícito: construtor aceita `rbac_checker=permitir_tudo` importável (`from kabbalah.firewall_mcp import permitir_tudo`) — a permissividade tem que ser opt-in visível no código do chamador, nunca default.
  4. Corrigir os testes que constroem `FirewallMCP()` puro (vão passar a ser negados — atualize-os para injetar `permitir_tudo` quando o teste não for sobre RBAC).
  *Aceite*: `FirewallMCP()` sem checkers nega tudo; bridge continua funcionando (já injeta); commit documenta a mudança de default.
- [x] **6.2 (M6) Log no enforcement principal** *(Claude, 2026-07-04)* — em `src/kabbalah/fsm_enforcement.py`: `check_operation_allowed` (linha 162) não loga; `check_operation_allowed_with_logging` (linha 180) loga. Unificar: a variante principal SEMPRE loga bloqueios; `_with_logging` vira alias deprecated (manter por compat, com `DeprecationWarning`).
  *Aceite*: teste provando que um BLOCK pelo caminho principal gera registro de auditoria; grep confirma que nenhum caller depende da variante sem log para silêncio.

---

### ONDA 7 — Budget Manager (M12) — esforço: 2-3 dias — depende da Onda 5

Objetivo: custo passa a ser controlado, não só acumulado. Insumo: `total_cost` já é acumulado por provider (`base.py:57,165`) e exposto em `get_stats()` — falta quem leia e haja.

- [x] **7.1** Estender `src/kabbalah/budget_manager.py`: o `BudgetLedger` append-only já existe desde a Onda 5; adicionar `BudgetManager` com limites configuráveis (por run, por dia, por provider) via env `KABBALAH_BUDGET_*`.
- [x] **7.2** Integração: o **LLMGateway consulta o BudgetManager antes de retornar provider**; estourou → exceção clara `BudgetExceededError` (modo `block`) ou warning logado (modo `warn`). **Default: `warn`** na primeira release; `block` via `KABBALAH_BUDGET_MODE=block`.
- [x] **7.3** Expor `get_budget_stats` como tool no bridge (mesmo padrão de `get_network_stats`).
  *Aceite*: teste de limite estourado nos dois modos; ledger append-only (sem API de update/delete); leaf registra custo no ledger a cada execução; suíte verde.
- [x] **7.4 Achados da ignição real (smoke Groq, 2026-07-04)** — dois defeitos
  observados na primeira chamada LLM de verdade, ambos escopo desta onda:
  1. **Fallback por candidato**: com Ollama offline (`localhost:11434` recusou),
     o gateway selecionou o perfil local (cheap-first correto) e o leaf FALHOU
     em vez de escalar. Corrigir: falha de conexão/instanciação marca o
     candidato como indisponível (com registro) e tenta o PRÓXIMO da lista;
     só falha quando todos os candidatos esgotarem. Teste simulando conexão
     recusada no primeiro perfil.
  2. **Custo real no ledger**: a chamada Groq real gravou `cost: 0.0` — o
     `OpenAICompatibleProvider` não conhece pricing. Calcular custo a partir
     do pricing do `ModelProfile` × `usage` reportado e gravar no ledger com
     precisão suficiente para micro-custos (não arredondar para zero).

---

### ONDA 8 — Features visíveis + AJUSTES FINOS (M8+M9+config+polimento) — esforço: 2-3 semanas — depende das Ondas 5 e 7

- [x] **8.-1 Achados do teste REAL de matriz de providers (2026-07-04, chaves live do Charles)** *(Codex, 2026-07-04 — testes em `tests/test_llm_gateway.py`, `tests/test_mistral_provider_unit.py`, `tests/providers/test_openai_compatible_provider.py`)* —
  probe ao vivo de 1 frase por tier. **Estes são bugs reais, prioridade nesta onda:**
  1. **Modelos premium DOA (bug de config)**: os defaults do registro `gpt-4.1`,
     `gemini-pro` e `mistral-large-latest` NÃO existem na allowlist dos providers
     nativos (`openai_provider.py` aceita `gpt-4o/gpt-4-turbo/gpt-4`;
     `google_gemini_provider.py` aceita `gemini-2.5-flash/2.5-pro/2.0-flash/pro-latest`;
     `mistral_provider.py` aceita `mistral-large`) → `ValueError: Unknown model`.
     Com os ids corretos, os três funcionam (testado: OpenAI $4.5e-5, Gemini
     $6.75e-7). Corrigir os defaults do `CapabilityRegistry.default()` para ids
     válidos e adicionar teste que valide profile.model contra a allowlist do
     provider nativo correspondente.
  2. **Cerebras 404**: `https://api.cerebras.ai/v1/chat/completions` retornou
     Not Found — base_url/rota incorreta. Verificar o endpoint atual da Cerebras.
  3. **SambaNova 410 GONE**: endpoint desativado — atualizar base_url/modelo para
     a API vigente ou marcar o perfil como indisponível por padrão.
  4. **Mistral resposta vazia**: conecta e autentica, mas retornou content vazio
     e 0 tokens com `mistral-large` — investigar parsing da resposta no
     `mistral_provider.py` (pode ser formato de retorno ou `max_tokens`).
  **Status da correção**: defaults premium agora usam modelos aceitos pelos
  providers nativos (`gpt-4o`, `gemini-2.5-pro`, `mistral-large`); Cerebras e
  SambaNova mantêm os base URLs OpenAI-compatible oficiais e usam modelos
  atuais (`gpt-oss-120b`, `Meta-Llama-3.3-70B-Instruct`); Mistral normaliza
  conteúdo retornado como string, dict, objeto ou lista de text chunks.
  **Confirmado funcionando ponta a ponta com chave real**: OpenRouter, Groq,
  OpenAI, Gemini (custo real gravado no ledger; enforcement `block` levantou
  `BudgetExceededError`, `warn` permitiu com decisão negada). O caminho barato
  padrão (OpenRouter+Groq) está sólido; os premium precisam só do ajuste de id.

> Decisão do Charles (2026-07-04): esta é a **onda do acabamento**. As ondas
> anteriores são o grosso; o propósito final é um sistema **limpo e belo** —
> instalável em 5 minutos, com toda mensagem de erro dizendo o que fazer, e
> cara de produto no GitHub. Cada onda continua entregando limpo (regra §2),
> mas o passe de vitrine concentrado é aqui.

- [x] **8.0 Configuração e onboarding (menu de configurações)** *(Codex, 2026-07-05 — testes em `tests/test_onboarding.py`, `tests/test_configuration_manager.py`, `tests/test_cli.py`)* — chaves são
  **por instalação e solicitadas ao usuário**, nunca embutidas no projeto:
  1. **Primeiro boot sem config** → wizard interativo na CLI (`kabbalah setup`):
     lista os providers do registro, usuário escolhe quais ativar, insere as
     chaves com input oculto (`getpass`), o wizard **valida cada uma com uma
     chamada de teste** e só então armazena.
  2. **Armazenamento por instalação**, em ordem de preferência: keyring do SO
     (Windows Credential Manager / Secret Service, via lib `keyring`) como
     padrão; Bitwarden via `CofreBitwarden` como opção avançada (o projeto já
     prega isso); `.env` local como fallback de dev. **Nunca** em arquivo
     tracked, nunca em claro no state DB.
  3. **Menu `kabbalah config`**: listar providers com status da chave (presente/
     válida/ausente — exibir no máximo últimos 4 caracteres), adicionar/remover/
     testar chave, ver perfil de hardware ativo, definir limites de budget
     (integra Onda 7), escolher política de roteamento.
  4. **Nunca pedir segredo em execução autônoma**: se o gateway precisar de um
     tier sem chave durante um run, falha com instrução clara para rodar
     `kabbalah setup` — input de segredo só em sessão interativa do humano.
  5. Bridge: expor `get_config_status` (status sem valores) como tool.
  6. Existe `src/kabbalah/configuration_manager.py` (com testes) — **leia e
     estenda**, não crie um sistema paralelo.
  *Implementado*: `kabbalah setup` lista providers, recebe chaves por input
  oculto, valida com chamada mínima via provider e só então armazena no
  keyring; `kabbalah config list/add-key/remove-key/test-key/set-budget/
  set-routing` cobre status seguro, hardware ativo conhecido, limites de
  budget e política de roteamento; `get_config_status` permanece exposto no
  bridge sem valores secretos.
  *Aceite*: instalação limpa → wizard funciona ponta a ponta; nenhum segredo
  aparece em arquivo tracked, log ou saída de `kabbalah config list`; chave
  inválida é rejeitada na validação; suíte verde.
- [x] **8.1 (M8) Model Comparison** *(Codex, 2026-07-04 — testes em `tests/test_model_comparison.py` e `tests/test_sillytavern_mcp_bridge.py`)* — nova tool `compare_models` no bridge: mesma task despachada a N providers (via gateway, respeitando budget), retorna tabela JSON: provider, latência, tokens, custo, resposta. Passa pelo pipeline de segurança normal (contrato + firewall + qlipot) como qualquer tool. Sem API keys live configuradas → erro honesto por provider, não mock.
  *Nota*: o payload de autorização sanitiza o campo técnico `max_tokens` como
  `output_limit` para evitar falso positivo do Qlipot sobre a palavra "token";
  o executor continua usando `max_tokens` real na chamada ao provider.
  *Aceite*: teste com MockProvider gated simulando 2 "providers"; entrada documentada no README.
- [x] **8.2 (M9) Group Chat SillyTavern** *(Codex, 2026-07-05 — testes em `tests/test_sillytavern_group_chat.py`, `tests/test_sillytavern_group_chat_docs.py`, `tests/test_sillytavern_mcp_bridge.py`)* — mapear orquestração para sala ST: cada domain = um bot; decisões do Firewall/HITL aparecem como mensagens. Item mais aberto — **produza primeiro um design doc curto** (`docs/specs/st-group-chat-design.md`) com o mapeamento proposto e critérios, e só então implemente. Se o esforço explodir (>5 dias), pare no design doc e reporte.
  *Implementado*: design doc criado em `docs/specs/st-group-chat-design.md`;
  renderer `src/kabbalah/sillytavern_group_chat.py`, tool MCP
  `render_group_event`, e exemplo MCP-only em
  `docs/examples/sillytavern/kabbalah-group-chat/` com Blank Cards e routing.
- [x] **8.3 CLI e experiência de uso** *(Codex, 2026-07-05 — testes em `tests/test_cli.py`; exit codes em `docs/specs/cli-exit-codes.md`)* — a interface tem que ser bonita e
  consistente:
  1. `kabbalah status` — painel único: perfil de hardware ativo, providers e
     saúde das chaves (sem valores), gasto do dia (ledger), contratos ativos,
     tickets HITL pendentes.
  2. Toda mensagem de erro no formato **o que aconteceu → por quê → o que
     fazer** (com o comando sugerido). Vale para CLI, bridge e exceções públicas.
  3. Saída com cores/tabelas legíveis (lib `rich`) + flag `--json` em todo
     comando para consumo por máquina; exit codes documentados e consistentes.
  4. Logging estruturado: silencioso por padrão, `-v/-vv` progressivo, nunca
     poluir stdout do bridge (stdio MCP é sagrado).
  *Implementado*: `kabbalah status --json` e painel texto/rich incluem config
  segura, budget, hardware ativo conhecido, contratos ativos e tickets HITL
  pendentes; `-v/-vv` aumentam logging; JSON errors usam `what_happened/why/
  what_to_do`; exit codes documentados.
- [x] **8.4 Empacotamento moderno** *(Codex, 2026-07-05 — testes em `tests/test_packaging_metadata.py`)* — migrar `setup.py` → `pyproject.toml`
  (PEP 621), single-source da versão (`kabbalah.__version__`), criar
  `CHANGELOG.md` retroativo por ondas (semver: 0.x enquanto alpha), extras
  opcionais formalizados (`pip install kabbalah[mcp,memory,observability]`)
  substituindo os requirements-*.txt na documentação (mantê-los como espelho).
  *Aceite*: `pip install -e .` e extras funcionam; versão única em um lugar.
  *Implementado*: `pyproject.toml` é a fonte canônica PEP 621; `setup.py`
  permanece como shim legado; versão vem de `kabbalah.__version__`; extras
  `mcp`, `memory` e `observability` formalizados; `requirements-*.txt` ficam
  como espelhos; `CHANGELOG.md` registra o histórico por ondas.
- [x] **8.5 CI no GitHub** *(Codex, 2026-07-05 — testes em `tests/test_ci_workflow.py`)* — hoje `.github/` só tem templates. Criar workflows:
  1. `ci.yml`: suíte completa em push/PR (Windows + Ubuntu, Python 3.9 e 3.11),
     ruff check, e job de gitleaks.
  2. Badges REAIS no README (build, versão, licença) — badge verde de verdade,
     não decorativo.
  *Aceite*: pipeline verde no primeiro push; PR sem testes falha o check.
  *Implementado*: `.github/workflows/ci.yml` roda ruff e pytest em
  Windows/Ubuntu com Python 3.9/3.11 e inclui job separado de gitleaks; README
  usa badges reais de workflow, tag de versão e licença do GitHub.
- [ ] **8.6 Qualidade de código fina** — ampliar `ruff.toml` além de F401/F841
  (adicionar `E`, `W`, `I` para ordenação de imports, `B` bugbear), corrigir o
  que apontar; type hints completos nos módulos públicos (gateway, contratos,
  firewall, cofre, profiler); docstring em toda classe/função pública seguindo
  o padrão do repo. Sem reescrever lógica — só acabamento.
- [ ] **8.7 Documentação-vitrine** — o README é a cara do produto:
  1. Reescrever o README como pitch honesto: o que é (kernel de governance),
     demo em 5 minutos (quickstart testado do zero numa máquina limpa),
     diagrama de arquitetura renderizado (mermaid), GIF/asciinema do
     `kabbalah setup` + um run governado de exemplo.
  2. `docs/ARCHITECTURE.md` ganha os diagramas atualizados pós-Onda 5
     (gateway, registro, profiler).
  3. Guia "instalando em 5 minutos" validado por execução real em clone limpo.
  *Aceite*: um dev que nunca viu o projeto instala e roda o demo só com o
  README, sem perguntar nada.

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
- Não confiar em nenhum documento da raiz exceto `README.md`; a análise estratégica vive em `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md`, e a verdade operacional está em `docs/` e no código.

### ONDA 11 — Rede federada (SyncHub fase 2) — **só após a Onda 9 (M17)**

> Gate duro: federar exige o Kabbalah-Bench provando com números que correções
> compartilhadas melhoram contenção. Federar sinal não-validado é distribuir
> ruído (ou veneno) em escala. Decisões abaixo fechadas com o Charles em
> 2026-07-04 (recomendação do Claude, veto do Charles a qualquer momento).

Visão: **threat intelligence federada para agentes** — o modelo "definições de
antivírus", não uma rede social de instâncias. O SyncHub atual é a metade local
(sinapses, quarentena, reputação, ban list); esta onda cria o transporte.

- [ ] **11.1 Design doc primeiro** — `docs/specs/federated-network-design.md`:
  formato do bundle, pipeline de importação, modelo de ameaça (envenenamento,
  spoofing, replay), plano de compatibilidade entre versões do assessor.
- [ ] **11.2 Identidade criptográfica** — keypair ed25519 gerado no
  `kabbalah setup` (integra 8.0); a chave pública é a identidade da instância
  na rede. O `hardware_hash` do profiler vira telemetria, NÃO identidade.
- [ ] **11.3 Bundles assinados (a "rede" sem servidor)** — exportar/importar
  arquivos de sinapses assinados:
  - Conteúdo por sinapse: `hash(assinatura_acao)`, delta, contadores, janela
    temporal grosseira, `RISK_ASSESSOR_VERSION`. **Nunca** conteúdo bruto
    (parâmetros, caminhos, prompts não saem da máquina).
  - Bundle carrega identidade do publicador + assinatura ed25519.
  - Importação: verificar assinatura → publicador na trust list → quarentena →
    quórum (≥N publicadores independentes OU contagem mínima) → clamp ±0.30
    (já existe) → `aplicar_correcao(origem="sync_hub")` → auditoria append-only.
  - Correção só internaliza se `RISK_ASSESSOR_VERSION` for compatível.
- [ ] **11.4 Trust list e modos** — chave do projeto (Charles) pré-confiada;
  usuário gerencia via `kabbalah config` (trust add/remove). Modos de rede no
  menu 8.0: `off` (DEFAULT — instalação nunca fala com rede sem ação explícita)
  / `receber` (importa, não envia) / `receber+contribuir`.
  - Distribuição fase 2: bundles oficiais curados e assinados pelo Charles via
    GitHub Releases do repo. Formato neutro por design: qualquer publicador
    pode assinar; a trust list de cada dono decide.
- [ ] **11.5 Medir antes e depois** — rodar o Kabbalah-Bench com e sem as
  correções importadas; só promover a feature se a taxa de contenção melhorar
  sem aumento de falso-positivo.

Fases 3 (hub HTTPS opt-in) e 4 (P2P gossip): futuro, cada uma gated por tração
real da fase anterior — NÃO especificar agora.

## 5. DEFINIÇÃO DE PRONTO (por onda)

1. Todos os checkboxes da onda marcados neste arquivo.
2. Suíte completa: 0 failed (passed pode crescer; 89 skipped constantes).
3. Um commit por item, hook de segredos verde.
4. README/docs atualizados se comportamento visível mudou.
5. Divergências encontradas registradas neste doc (seção nova "Divergências" ao final, se necessário).

## 6. DECISÕES PENDENTES DO CHARLES (gates)

| # | Decisão | Bloqueia |
|---|---|---|
| 1 | ✅ Resolvido 2026-07-04 — ondas 1–6 mergeadas em `main` (fast-forward, sem push) | — |
| 2 | E2B (pago/cloud) vs Firecracker (self-hosted/Linux) | Onda 10.1 |
| 3 | Modelo ML para o Qlipot + orçamento de avaliação | Onda 10.2 |
| 4 | ✅ Resolvido 2026-07-04 — smoke real executado via Groq (`llama-3.1-8b-instant`): leaf → gateway → provider → artifact + linha no ledger. Achados registrados no item 7.4 | — |
