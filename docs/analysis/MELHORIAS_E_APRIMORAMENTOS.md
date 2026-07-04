# Kabbalah — Análise Completa, Melhorias e Aprimoramentos

> **⚠️ PAPEL DESTE DOCUMENTO — leia antes de agir**: este arquivo é a **análise
> estratégica de entrada** (levantamento externo). Ele NÃO é o plano de execução
> canônico e contém claims técnicos desatualizados (ex.: estado dos testes,
> M4/M7 já aplicados nas ondas 2–3). A execução canônica, reconciliada com o
> código real, está em `docs/roadmap/handoff-execution-plan.md` (§0 traz a tabela
> do que daqui já foi feito ou envelheceu). Em divergência, o handoff vence.
> Hierarquia completa de documentos: `docs/ops/context-pack.md`.

> **Documento técnico consolidado** — geração: 2026-07-04
> **Escopo**: raio-x do código (não do README), origem das linhagens, auditoria dos subsistemas, comparativo de mercado e plano de melhorias priorizado.
> **Premissa do projeto**: a equipe de LLM está parada; o foco tem sido a camada de **controle/governance**, que está mais madura que a de LLM. Este doc parte dessa realidade.

> **Atualização Codex — 2026-07-04**: este documento foi comparado com o estado atual do checkout em `hardening/wave-2`. As afirmações abaixo agora distinguem: (a) achados históricos, (b) pontos já corrigidos pelas Waves 1/2/3, e (c) lacunas ainda abertas.
>
> **Status vivo**: a fonte canônica de execução é `docs/roadmap/handoff-execution-plan.md` §0. Este arquivo permanece como análise estratégica de entrada em `docs/analysis/`, não como ordem de implementação.

---

## ESTADO ATUAL VERIFICADO — 2026-07-04

Branch local verificada inicialmente: `hardening/wave-2`; limpeza em execução na branch `wave-4-hygiene`.

Histórico recente relevante:

- `63a1525 security: harden bridge and execution engine wave 1`
- `f48568b security: persist agent contracts with auditable store wave 2`
- `69c7850 security: harden risk scoring and vault wave 3`

Validação focal executada nesta revisão:

```text
pytest tests/test_bridge_hardening_wave1.py \
       tests/test_bridge_hardening_wave2.py \
       tests/test_qlipot_hardening_wave3.py \
       tests/test_contrato_store.py \
       tests/test_cofre.py \
       tests/test_sillytavern_mcp_bridge.py -q

64 passed
```

Suíte completa executada nesta revisão:

```text
pytest tests -q → 1127 passed, 89 skipped em 157.77s
```

Validação durante a limpeza da Onda 4:

```text
ruff check src tests kabbalah_mcp_bridge.py → All checks passed
pytest tests -q → 1127 passed, 89 skipped
```

### Correções já incorporadas desde a versão original deste documento

| Área | Antes no documento | Estado atual verificado |
|---|---|---|
| Bridge MCP | Contratos ainda pouco endurecidos | Wave 1: contratos fail-closed por padrão, allowlist de path/env, anti-SSRF, shell opt-in, tickets HITL em SQLite, I/O em `asyncio.to_thread` |
| ToolExecutionEngine | "Sandbox falso" com grep/shell vulnerável | Wave 1: grep sem `shell=True`, contenção de path com `Path.resolve()`, validação de domínio contra suffix confusion, anti-SSRF e kill-switch de bash |
| Contratos | Estado só em memória | Wave 2: `ContratoStore` SQLite, reload de contratos persistidos, eventos auditáveis, ausência de contrato separada de violação, consumo de `max_calls` via SQL |
| Qlipot | Keyword lowercase puro; `aplicar_correcao` sem auth | Wave 3: normalização NFKC/casefold, remoção de format chars, mapeamento parcial de homoglyphs, scan de payload base64, padrões críticos, versão de assessor e correções autorizadas/clampadas/auditadas |
| Cofre | `bw` via PATH sem validação; cache plaintext sem mitigação | Wave 3: `BITWARDEN_CLI_PATH`, hash opcional `KABBALAH_BW_SHA256`, `clear_on_read`, documentação explícita do tradeoff de cache |
| CLI | Apontava para `cli.py` inexistente | Onda 4: `src/kabbalah/cli.py` e entrypoint `kabbalah` validados com `--help` |
| Higiene de repo | `openclaude/`, specs antigas, relatórios raiz e exports de mock poluíam o repo/API | Onda 4: `openclaude/` removido, specs `.kiro` arquivadas, relatórios raiz arquivados/removidos quando duplicados, `MockProvider` removido do export público |

### Lacunas que permanecem abertas

- `LeafNode` ainda não chama provider real: `_execute_leaf_node()` continua retornando artifacts vazios.
- `LLMGateway` continua órfão do runtime principal.
- `CogneeBackend` ainda é placeholder; JSONL é o fallback real.
- `FirewallMCP` ainda tem RBAC default `_allow_all`; precisa política deny-by-default ou modo produtivo explícito.
- `fsm_enforcement.check_operation_allowed()` ainda precisa garantir log/auditoria no caminho principal.
- Ainda não há sandbox real tipo E2B/Firecracker/gVisor; o engine foi endurecido, mas continua executando localmente quando habilitado.

## SUMÁRIO EXECUTIVO

O Kabbalah é um **kernel de segurança e governance para agentes LLM** (não um orquestrador genérico). A análise de código real (não dos relatórios de marketing) mostra:

- **A camada de CONTROLE está genuinamente implementada e testada** (Qlipot, FirewallMCP, HITL, Contratos, Cofre) — é o diferencial real e raro no mercado.
- **A camada de LLM existe, mas está DESCONECTADA** — os providers funcionam, mas o `LeafNode` nunca os chama. O motor tem chassis mas falta a correia.
- **Os relatórios antigos de "fase completa / aprovado para produção" não devem ser usados como fonte de verdade**. O código evoluiu bastante desde a auditoria de 2026-04-11; use sempre o checkout atual e a suíte atual como referência.
- **A positioning ótimo é "MCP security gateway / action-authorization kernel"** — um mercado quase vazio, enquanto frontends (SillyTavern), workspaces (Odysseus/Open WebUI) e memória (Cognee/Mem0) estão saturados. Mesmo a Sakana AI (lab de pesquisa de ponta em agentes autônomos) foca na *inteligência* do agente (tree search, evolução) e **não** na contenção — confirmando que a lacuna de governance está aberta inclusive na fronteira de pesquisa.

---

## PARTE 1 — RAIO-X DO CÓDIGO REAL

### 1.1 Volume e proporção

| Camada | Arquivos | Linhas |
|---|---|---|
| `src/kabbalah/` (código) | 53 | ~15.807 |
| `tests/` | 69 | ~24.994 |
| `kabbalah_mcp_bridge.py` (artefato-chave) | 1 | 833 |

Proporção teste/código ~1,6:1 — saudável. O projeto **tem cultura de teste** (Hypothesis, 51 propriedades de correção formal especificadas).

### 1.2 O que está implementado de verdade

| Subsistema | Estado | Evidência |
|---|---|---|
| Qlipot (avaliador de intenção) | ✅ Real, testado | `qlipot.py`, scoring com memória temporal |
| FirewallMCP (autorizador) | ✅ Real, testado | `firewall_mcp.py`, RBAC+contrato+risco+HITL |
| HITL (approvação humana) | ✅ Real, testado | `hitl.py`, fail-safe por padrão |
| Contratos (agent-to-agent) | ✅ Real, persistente e testado | `contratos.py` + `contrato_store.py`, propose/sign/reject/violação/ausência |
| Cofre (Bitwarden) | ✅ Real, testado e endurecido | `cofre.py`, repr esconde valor, exige BW_SESSION, `BITWARDEN_CLI_PATH`, hash opcional |
| SyncHub (aprendizado federado) | ⚠️ Real mas local | `sync_hub.py`, sinapses/quarentena/reputação |
| AutonomyLoop (replanning) | ✅ Real | `autonomy_loop.py`, max_retries |
| Providers (OpenAI/Groq/Mistral/Together/DeepSeek) | ✅ Implementados, **não conectados** | ninguém os chama em runtime |
| LLMGateway (seleção por $) | ✅ Implementado, **órfão total** | só referenciado em si mesmo |
| LeafNode → provider | ❌ **Lacuna central** | `domain_orchestrator.py:215` retorna vazio |
| RootOrchestrator | ⚠️ Bugado | dependências comparadas no domínio errado |
| Memory Cognee | ❌ Placeholder | `memory_subsystem.py:73-109` é stub |
| Tool sandbox | ⚠️ Endurecido, mas não isolado | grep sem shell, path/SSRF hardening, kill-switch de bash; ainda não é micro-VM |
| CLI | ✅ Validada | `python -m kabbalah.cli --help` e `kabbalah --help` exit 0 |

### 1.3 Resultado dos testes

Histórico antigo, útil apenas como referência forense:

```text
2026-04-11: PYTHONPATH='.;src' pytest tests -q → 812 passed / 74 failed / 4 skipped
```

Estado atual verificado nesta revisão:

```text
Focused hardening/bridge set → 64 passed
Full suite                  → 1127 passed / 89 skipped
```

Observação: a suíte já teve flake conhecido de deadline Hypothesis em `tests/test_memory_governance_properties.py`. Se uma falha isolada aparecer ali, rerodar o teste antes de tratá-la como regressão do patch.

---

## PARTE 2 — ORIGEM DO CÓDIGO (FORENSE)

### 2.1 Não há cópia de terceiros

Rastreadas strings de origem (`@author`, `copyright`, `adaptado de`, `based on`, `fork`, `ported from`, `github.com/`) em todo `src/`. **Zero evidências de cópia.** O código é original.

### 2.2 Duas linhagens de nomenclatura

- **Português** (`cofre`, `contratos`, `qlipot`, `tradutor_local`, `sync_hub`) → design próprio/conceitual, a "alma" cabalística.
- **Inglês** (`firewall_mcp`, `hitl`, `autonomy_loop`, `llm_gateway`, `root_orchestrator`) → geração técnica, padrão operacional.

Isso indica **múltiplas mãos/múltiplos motores de IA** trabalhando em camadas diferentes.

### 2.3 Os motores de IA que passaram pelo projeto

A própria pasta `docs/audit/` contém laudos periciais que revelam a linhagem:

| Ferramenta | Papel | Evidência |
|---|---|---|
| **Kiro** (AWS) | Gerou specs formais | `.kiro/specs/`, `.config.kiro`, workflow "Requirements-First" |
| **Antigravity** (Google) | Auditou/gerou módulos | `LAUDO_PERICIAL_ANTIGRAVITY.md` assinado por "Antigravity (Google DeepMind)" |
| **Codex** (OpenAI) | Gerou módulos | `PERICIA_CIRURGICA_CODEX_2026_04_07.md` |

**Conclusão**: o código foi **gerado por agentes de codificação IA** (Kiro/Antigravity/Codex) sob direção humana (Charles Nóbrega, único autor dos commits). Não é fork de LangGraph/CrewAI/Sakana. O "OpenClaude" no nome é aspiracional — o repo clonado em `openclaude/` **não é usado pelo runtime** (auditoria confirma: nenhum import aponta pra ele).

### 2.4 Lixo identificado

- `openclaude/` — repositório Git inteiro clonado (TypeScript/Node), **não integrado**. Risco de supply-chain. **Remover.**
- `archive/legacy/` — snapshots de código antigo (error_detection_module duplicado). Indexar ou purgar.
- ~30+ relatórios de "PHASE X COMPLETE" conflitantes na raiz. **Polui navegação.** Há plano de cleanup em `REPOSITORY_STRUCTURE.md`.

---

## PARTE 3 — AUDITORIA DOS SUBSISTEMAS (CONTROLE)

### 3.1 Qlipot (avaliador de intenção)

| Achado | Sev | Detalhe |
|---|---|---|
| **Heurística keyword-based ainda é frágil** | 🟡 Médio | Wave 3 corrigiu o bypass raso: normalização NFKC/casefold, remoção de chars invisíveis, homoglyphs parciais, base64 e padrões críticos. Ainda falta substituir/acompanhar por classificador semântico/ML e benchmark de evasão. |
| **Faixa 0.61–0.95 não bloqueia de fato** | 🟡 Médio | `>0.60` só vai pra "diálogo". Não há gate real entre 0.61 e 0.95. |
| **Memória temporal O(n) por query** | 🟡 Médio | `_ultimas_acoes_agente` (linha 246) faz `query_knowledge(limit=100)` e filtra em Python. |
| **`aplicar_correcao` precisava auth** | ✅ Resolvido em Wave 3 | Agora exige origem autorizada, limita delta por clamp e registra tentativa/aplicação em audit trail com versão do assessor. |

### 3.2 FirewallMCP (autorizador)

| Achado | Sev | Detalhe |
|---|---|---|
| **`_default_risk_assessor` é keyword-based** | 🟡 Médio | Ainda existe como fallback simples. O risco operacional caiu porque o bridge passa risco do Qlipot endurecido, mas a biblioteca isolada ainda precisa assessor versionado/semântico. |
| **`check_operation_allowed` não loga** | 🔴 Alto | `fsm_enforcement.py:156` — só a variante `_with_logging` loga. BLOCK pode acontecer sem registro. Viola requisito de audit imutável. |
| **RBAC padrão é `_allow_all`** | 🔴 Alto | `firewall_mcp.py:85` — sem `rbac_checker` injetado, **tudo passa**. |
| **`verificar_contrato` fallback confuso** | 🟡 Médio | Parcialmente mitigado pelo bridge fail-closed e `contract_verifier`, mas o fallback de biblioteca ainda merece simplificação/remoção. |

### 3.3 Contratos (agent-to-agent)

**A parte mais sólida.** Ideia genuinamente boa — agentes precisam propor→assinar contratos antes de cross-actions.

| Achado | Sev | Detalhe |
|---|---|---|
| **Estado só em memória** | ✅ Resolvido em Wave 2 | `ContratoStore` SQLite persiste contratos e recarrega no construtor. O bridge usa o mesmo state DB para HITL/contratos. |
| **`_find_active` O(n)** | 🟡 Médio | Ainda há cache/dict em memória; o store já dá base para índices, mas a busca runtime ainda pode ser otimizada por `(provedor, acao, status)`. |
| **`chamadas` não é thread-safe** | ✅ Resolvido em Wave 2 quando store ativo | `max_calls` é consumido via operação SQL atômica em `ContratoStore.consume_call()`. Sem store, o fallback em memória segue apenas para uso simples/testes. |
| **ID não verificável** | 🟢 Baixo | `contract_{uuid4().hex[:12]}` — truncado, não assinado cripto. Agent poderia forjar. |

### 3.4 Cofre (Bitwarden)

**Bom design, boa higiene.** `__repr__` esconde valor, exige `BW_SESSION`, nunca lê `.env`.

| Achado | Sev | Detalhe |
|---|---|---|
| **Cache plaintext em memória** | 🟡 Médio | Tradeoff agora está documentado; `clear_on_read=True` existe para segredos críticos. Ainda não há criptografia em RAM. |
| **`subprocess.run(["bw",...])` sem path validado** | ✅ Resolvido em Wave 3 | `BITWARDEN_CLI_PATH` permite fixar o binário e `KABBALAH_BW_SHA256` valida hash opcional. |

---

## PARTE 4 — AUDITORIA DA CAMADA LLM

### 4.1 O diagnóstico principal (uma frase)

> **Os providers existem e funcionam, mas NADA no sistema os chama.** O `LeafNode` — onde o LLM deveria ser invocado — retorna `status="success"` com `artifacts=[]` sem nunca chamar nenhum provider. É um motor sem correia.

### 4.2 Prova em código

**O leaf é mudo** (`domain_orchestrator.py:215-236`):
```python
def _execute_leaf_node(self, leaf_node):
    # In a real implementation, this would execute the task
    # using the assigned provider and tools
    return LeafResult(status="success", artifacts=[], metadata={})
```

**LLMGateway é órfão**: varredura mostra que `LLMGateway`/`selecionar_provider` **só aparecem no próprio arquivo**. Nenhum módulo os importa.

**LocalLLMProvider (Ollama)**: só usado em `error_analysis_module.py` (self-healing). Não entra na factory, não é opção do leaf.

### 4.3 Inventário LLM

| Componente | Existe? | Funciona? | Conectado? |
|---|---|---|---|
| `BaseProvider` (interface) | ✅ | ✅ | ✅ |
| OpenAI/Groq/Mistral/Together/DeepSeek | ✅ | ✅ | ❌ ninguém chama |
| GoogleGemini | ✅ | ⚠️ SDK deprecated, env var inconsistente | ❌ |
| MockProvider | ✅ | ✅ | ✅ não exportado publicamente; uso por módulo dedicado de teste |
| LocalLLMProvider (Ollama) | ✅ | ✅ | ⚠️ só em error_analysis |
| ProviderFactory | ✅ | ✅ | ❌ órfão |
| LLMGateway (seleção por $) | ✅ | ✅ | ❌ órfão total |
| Anthropic/Claude | ❌ | — | Fora do README atual; não é provider implementado |
| **LeafNode → provider** | ❌ | — | **lacuna central** |

### 4.4 Lacunas LLM priorizadas

**🔴 P1 — Fechar o loop**
1. Conectar LeafNode ao provider (instanciar factory → `execute_request` → empacotar artifact).
2. Decidir gateway canônico (Factory por role vs LLMGateway por $ — hoje dois becos).

**🟡 P2 — Qualidade**
3. Anthropic/Claude não existe; manter fora do README até existir provider real.
4. Gemini deprecated + env var inconsistente + perde stats em erro.
5. Contagem de tokens em streaming é chute (`len/4` em PT/code erra).

**🟢 P3 — Madureza**
6. Fallback chain nunca testada ponta-a-ponta.
7. Sem circuit breaker por provider.
8. Streaming é capability morta (leaf é sync).
9. Sem cache de resposta.
10. Sem budget/cost enforcement (roadmap item 1, inexistente).

---

## PARTE 5 — COMPARATIVO DE MERCADO

### 5.1 As três camadas (Kabbalah não compete com os três projetos enviados)

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (UI/chat)                                  │
│  SillyTavern ← Kabbalah JÁ pluga via MCP bridge      │
├─────────────────────────────────────────────────────┤
│  WORKSPACE / APP (all-in-one)                        │
│  Odysseus AI, Open WebUI, AnythingLLM                │
├─────────────────────────────────────────────────────┤
│  MEMORY / DATA INFRA                                 │
│  Cognee ← Kabbalah JÁ usa como dependência           │
├─────────────────────────────────────────────────────┤
│  ★ GOVERNANCE / SECURITY KERNEL ★                    │
│  Kabbalah ← você está AQUI (camada rara)             │
└─────────────────────────────────────────────────────┘
```

### 5.2 Odysseus AI (odysseusai.dev) — workspace self-hosted

**O que é**: all-in-one. Chat, agentes autônomos (bash/files/web/memory), deep research, editor de docs, email (IMAP/SMTP), calendário (CalDAV), comparação de modelos, servidor MCP, ChromaDB. AGPL-3.0, ~69k★.

**Concorrentes dele**: Open WebUI (136k★), AnythingLLM (61k★).

**Por que explodiu**: integração competente de peças existentes (Ollama + ChromaDB + MCP + email/cal). Não há nada revolucionário tecnicamente.

**⚠️ A ameaça/oportunidade**: o Odysseus tem **agentes autônomos que usam bash/files/web** e **nenhuma camada de governance**. Se um agente rodar `rm -rf`, não há Qlipot/Firewall/HITL. **O Kabbalah é o que falta nele** — parceria potencial.

**O que roubar**:
- ✅ **Model fit scoring** — "qual modelo cabe na sua GPU". O Kabbalah tem `LLMGateway` órfão; isto resolve a UX dele.
- ✅ **Model comparison side-by-side + avaliação cega** — roda nos 6 providers e compara. Ouro pra demonstrar o gateway.
- ✅ **Postura local-first/privacy-first** como narrativa de marca.
- ✅ **MCP server nativo** — confirma que MCP virou padrão (você já acertou).

### 5.3 SillyTavern (docs.sillytavern.app) — frontend power-user

**O que é**: frontend LLM "for power users". Fork do TavernAI (fev/2023), 300+ contribuidores, 3 anos. NodeJS 20+. Character cards, world info, group chats (multi-bot), RAG built-in, engine de scripting, extensões (sprites, TTS, image gen, web search). AGPL-3.0.

**Já é o frontend do Kabbalah** via `kabbalah_mcp_bridge.py`. Acerto.

**O que roubar**:
- ✅ **Character cards como UX de "agent roles"** — `CanonicalRole` hoje é invisível. Vira card editável.
- ✅ **Group chats = orquestração visível** — em vez de Root→Domain→Leaf abstrato, mapear pra "sala com vários bots".
- ✅ **World Info** — substituto leve pras 51 propriedades de correção (hoje specs formais inacessíveis).
- ✅ **Engine de scripting** — expor Firewall/HITL como macros do ST.

⚠️ **Limitação**: ST é roleplay-centric. Se quiser parecer "enterprise/security", não fique só nele.

### 5.4 Cognee (docs.cognee.ai) — memória para IA

**O que é**: plataforma de memória. Pipeline: raw docs → chunks → entities → concepts → ontologias induzidas → searchable. Três verbos: **remember / improve / recall**. Pluggable: LLM, embeddings, vector stores, **graph DB**.

**Concorrentes**: **Mem0** (padrão de-facto, ~25k★), **Letta/MemGPT** (self-editing memory), **Zep** (longo prazo), **LangMem**. Cognee se diferencia por induzir **ontologias/grafo**.

**Já é dependência do Kabbalah** (`cognee==1.2.1`), mas a integração é **placeholder**. O fallback JSONL está **quebrado** (`ensure_consistency()` falha quando Cognee ausente).

**O que roubar**:
- ✅ **Ligar o Cognee de verdade** (tirar do placeholder). O Qlipot usa `MemorySubsystem` pra memória temporal de risco — cairia melhor em Cognee (semântico).
- ✅ **API remember/improve/recall** — mais limpa que `store_knowledge/query_knowledge`.
- ✅ **Graph DB** — o roadmap do Kabbalah tem "Graph Runtime" (item 8). Cognee já anda nisso.

### 5.5 Mapa competitivo do Kabbalah

```
                    AÇÃO/EXECUÇÃO
                          ▲
            Kabbalah ◀── aqui (raro!)
                          │
   ──────────────────────┼──────────────────────▶ CONTEÚDO/SAÍDA
        Lakera            │            Guardrails AI
        Prompt Security   │            NeMo Guardrails
        Patronus          │            Aporia
        (filtro de prompt │            (validação de I/O)
         e toxicidade)    │
                          ▼
```

**Insight central**: quase todos defendem **o que o modelo diz**. Quase ninguém defende **o que o agente faz**. O Kabbalah está numa célula de mercado pouco disputada: **action authorization / runtime governance para agentes autônomos sobre MCP**.

### 5.6 Concorrentes reais do kernel (pra estudar no GitHub)

| Projeto | Camada | Por que estudar |
|---|---|---|
| **Mem0** (mem0ai/mem0) | Memória | Padrão de-facto. Como evitaram o "placeholder hell". |
| **Letta** (letta-ai/letta) | Agente+memória | Como modelam "agent identity" — falta no Kabbalah. |
| **Guardrails AI** | Validação | Padrão de validator reusável — Qlipot poderia expor assim. |
| **NeMo Guardrails** (NVIDIA) | Rails | Como uma DSL de policy fica (a do Kabbalah está espalhada em Python). |
| **Llama Prompt Guard** (Meta) | Classificação | Alternativa ML aos keywords do Qlipot (resolve bug de case). |
| **E2B** | Sandbox | **O sandbox que o Kabbalah finge ter.** |
| **Invariant Labs** | Research agent security | O mais próximo filosoficamente. |

Em **MCP governance** especificamente (o nicho mais valioso): **não há líder open-source consolidado**. Janela aberta.

### 5.7 Sakana AI (sakana.ai / github.com/sakanaai) — lab de pesquisa, NÃO produto

> ⚠️ **Correção**: análise anterior subestimou a Sakana como "complementar". Dados de 2026 mostram **dois repositórios que são concorrentes diretos** de conceitos centrais do Kabbalah.

**O que é**: lab de pesquisa em Tóquio ("Building Frontier AI in Japan"), fundado por ex-DeepMind/Google (David Ha, Llion Jones). Mantra: **"nature-inspired intelligence"** — evolução, cardumes, biologia. 57 repositórios públicos, 3.7k followers. **Não é startup de produto; é lab que publica código.**

**Os 6 repositórios relevantes**:

| Repo | Stars | Sobreposição |
|---|---|---|
| **AI-Scientist-v2** | 6.7k | 🔴 DIRETA — "Agentic Tree Search" = orquestração em árvore |
| **AI-Scientist** | 14.1k | 🟡 Espírito de agente autônomo ponta-a-ponta |
| **CoffeeBench** | novo | 🔴 DIRETA — "Multi-Agent Economies" = contratos/reputação |
| **ShinkaEvolve** | 1.2k | 🟡 Self-healing evolutivo |
| **continuous-thought-machines** | 2k | 🟡 Leaf como processo iterativo |
| **evolutionary-model-merge** | 1.4k | 🟢 Fronteira de seleção de provider |

**As duas sobreposições diretas**:

1. **AI-Scientist-v2 × Orquestração em Árvore do Kabbalah**: o v2 usa "Agentic Tree Search" — decompor, explorar ramos em paralelo, podar, aprofundar. É a promessa do `Root→Domain→Leaf` do Kabbalah. **Diferença brutal: a Sakana implementou o algoritmo de busca; o Kabbalah só tem a forma da árvore** (`_execute_leaf_node` retorna vazio).

2. **CoffeeBench × Contratos/SyncHub do Kabbalah**: benchmark de "economias multi-agente heterogêneas" — agentes com capacidades diferentes negociando/transacionando em tarefas long-horizonte. É o sistema de `Contratos` + `SyncHub` do Kabbalah, mas com **dimensão econômica** e, crucialmente, com **forma de medir**.

**A grande diferença filosófica**:

| | Sakana | Kabbalah |
|---|---|---|
| Foco | Inteligência do agente (como pensa/busca/evolui) | Contenção do agente (como autorizar/auditar/conter) |
| Risco tratado | "Agente pode não ser inteligente o suficiente" | "Agente pode ser inteligente demais e perigoso" |
| Saída | Papers + código de pesquisa | Kernel operacional |

**São dois lados da mesma moeda.** Um agente Sakana (inteligente, autônomo, evolutivo) rodando **sem** um kernel Kabbalah é perigoso. Um kernel Kabbalah **sem** agentes inteligentes é vazio. **A integração é o objetivo, não a competição.**

**O que roubar de cada repositório**:

| Repo | Conceito | Aplicação no Kabbalah |
|---|---|---|
| **AI-Scientist-v2** | Tree search com pruning e budget | Transformar `AutonomyLoop` (replanning linear) em tree search com orçamento por ramo |
| **CoffeeBench** | Benchmark de economias multi-agente | Criar "Kabbalah-Bench": cenários onde agentes mal-comportados tentam ações perigosas; medir se Qlipot/Firewall/HITL os contém. **Hoje o Kabbalah não prova seu valor em números.** |
| **ShinkaEvolve** | Evolução de programas sample-efficient | `error_analysis` + `fix_generation` evolutivo: gerar N fixes, pontuar, recombina. Fecha com "Meta Evaluator" do roadmap |
| **continuous-thought-machines** | Raciocínio como processo iterativo | `LeafNode` como processo com checkpoints — encaixa perfeitamente com HITL (pausar no meio do raciocínio pra aprovar) |
| **evolutionary-model-merge** | Merge de modelos por evolução | Aspiracional: além de escolher provider (LLMGateway), merjar capacidades |

---

## PARTE 6 — PLANO DE MELHORIAS PRIORIZADO

Rank por **valor ÷ esforço**. Cada item tem: o quê, por quê, como, esforço estimado.

---

### 🥇 BLOCO 1 — FECHAR O LOOP (desbloqueia tudo)

#### M1. Conectar LeafNode ao Provider
- **O quê**: implementar `_execute_leaf_node` em `domain_orchestrator.py` para instanciar `ProviderFactory`, chamar `provider.execute_request()`, empacotar `ProviderResponse.content` como artifact.
- **Por quê**: sem isso, nada do projeto tem sentido — é o motor sem correia. Desbloqueia teste ponta-a-ponta, demo real e validação de todo o loop de controle.
- **Como**: ~200 linhas. Reaproveitar `ProviderFactory.get_provider_for_role()` + `leaf_node.description` como prompt.
- **Esforço**: 🟢 Baixo (1-2 dias).
- **Dependências**: nenhuma crítica.

#### M2. Consertar o Fallback de Memória
- **O quê**: quando Cognee ausente, JSONL deve permanecer funcional sem falhar `ensure_consistency()`.
- **Por quê**: o Qlipot depende de memória pra scoring temporal. Hoje o fallback quebrado envenena o kernel de segurança todo. O padrão Mem0/Cognee é "memória nunca derruba execução, só degrada".
- **Como**: separar `ensure_consistency` por backend; missing optional não poison healthy storage.
- **Esforço**: 🟢 Baixo (meio dia).
- **Dependências**: nenhuma.

#### M3. Decidir o Gateway Canônico
- **O quê**: unificar `ProviderFactory.get_provider_for_role()` (por role) e `LLMGateway.selecionar_provider()` (por $). Hoje são dois becos.
- **Por quê**: a seleção de provider é decisão estratégica (custo, latência, capacidade). Ter dois seletores não conectados é confusão arquitetural.
- **Como**: adotar `LLMGateway` como seletor de topo, `ProviderFactory` como construtor de instâncias abaixo.
- **Esforço**: 🟡 Médio (2-3 dias).

---

### 🥈 BLOCO 2 — FECHAR BURACOS DE SEGURANÇA

#### M4. Endurecer normalização e evasão básica do Qlipot + Firewall — ✅ Wave 3 aplicado
- **Estado atual**: hotfix aplicado no Qlipot: NFKC/casefold, remoção de chars invisíveis, mapeamento parcial de homoglyphs, scan de base64 e padrões críticos (`rm -rf`, `mkfs`, `dd if=`, `powershell -enc`, pipes para shell etc.).
- **O que permanece**: o fallback do Firewall ainda é keyword-based e o sistema ainda precisa de classificador semântico/ML e benchmark de evasão para substituir heurística pura.
- **Próximo passo**: M11 continua relevante, mas agora como evolução de robustez, não como hotfix emergencial.

#### M5. Tornar RBAC Deny-by-Default
- **O quê**: trocar `_allow_all` (`firewall_mcp.py:85`) por deny-by-default; exigir injeção explícita de `rbac_checker`.
- **Por quê**: hoje, sem checker injetado, **tudo passa no RBAC**. O bridge injeta, mas o padrão da biblioteca é perigoso.
- **Esforço**: 🟢 Baixo (horas).

#### M6. Logar no Caminho de Enforcement Principal
- **O quê**: `check_operation_allowed()` (`fsm_enforcement.py:156`) deve logar bloqueios, não só a variante `_with_logging`.
- **Por quê**: hoje um BLOCK pode acontecer sem registro de auditoria. Viola requisito de audit imutável.
- **Esforço**: 🟢 Baixo (horas).

#### M7. Persistir Contratos em SQLite — ✅ Wave 2 aplicado
- **Estado atual**: `ContratoStore` persiste contratos e eventos em SQLite; `Contratos(store=...)` recarrega contratos; `max_calls` é consumido por SQL atômico quando há store.
- **O que permanece**: melhorar índice runtime por `(provedor, acao, status)`, assinar IDs/contratos e expor relatórios auditáveis mais amigáveis.

---

### 🥉 BLOCO 3 — TRANSFORMAR CÓDIGO MORTO EM FEATURE

#### M8. Expor LLMGateway como "Model Comparison"
- **O quê**: transformar o gateway de seleção em feature visível — "rode esta task em N providers, compare custo/latência/qualidade".
- **Por quê**: rouba a UX do Odysseus (model comparison side-by-side). Vira demo matadora do gateway que hoje é código morto. Mostra valor imediato do `LLMGateway`.
- **Como**: endpoint no bridge + tabela no output.
- **Esforço**: 🟡 Médio (2-3 dias).

#### M9. Mapear Orquestração para Group Chat do SillyTavern
- **O quê**: `RootOrchestrator` vira uma "sala ST" onde cada domain é um bot; Firewall/HITL viram mensagens no chat.
- **Por quê**: ganha UX grátis (não reimplementa UI). Mostra o kernel funcionando de forma visível. Mapeia `CanonicalRole` para character cards editáveis.
- **Como**: adaptação do bridge para multiplexar bots.
- **Esforço**: 🟡 Médio (3-5 dias).

---

### 🏅 BLOCO 4 — ROBUSTEZ OPERACIONAL

#### M10. Adotar Sandbox Real (E2B ou Firecracker)
- **O quê**: substituir execução local por micro-VM (E2B), Firecracker ou gVisor para ações perigosas.
- **Por quê**: Wave 1 endureceu execução local (grep sem shell, path/SSRF hardening, bash kill-switch), mas isso ainda não é isolamento real.
- **Esforço**: 🟡 Médio (1-2 dias com E2B).
- **Dependências**: requer decisão de infra (E2B cloud vs self-hosted Firecracker).

#### M11. Trocar Keywords do Qlipot por Classificador ML
- **O quê**: plugar Llama Prompt Guard ou classifier treinado em vez de lista de keywords.
- **Por quê**: Wave 3 reduziu evasões óbvias, mas classificador semântico ainda é necessário para sinônimos, outro idioma, intenção indireta e prompts compostos.
- **Esforço**: 🔴 Alto (1-2 semanas — modelo, dataset, eval).

#### M12. Implementar Budget Manager (roadmap item 1)
- **O quê**: track de custo/token por run, com limites que **barram** execução (não só warn).
- **Por quê**: `_record_call` acumula `total_cost` mas ninguém lê. Sem isso não há controle financeiro de agentes autônomos.
- **Dependências**: M1 (sem leaf conectado, não há custo pra medir).
- **Esforço**: 🟡 Médio (2-3 dias).

#### M17. Criar o "Kabbalah-Bench" (benchmark de governance)
- **O quê**: conjunto de cenários onde agentes mal-comportados tentam ações perigosas (escalar privilégio, exfiltrar dados, rodar `rm -rf`, encadear tools perigosas) e mede-se a taxa de contenção do Qlipot/Firewall/HITL.
- **Por quê**: inspirado no CoffeeBench da Sakana (economias multi-agente) e no AI-Scientist-v2 (tree search). **O Kabbalah hoje não consegue provar seu valor em números.** Sem benchmark, "governance" é alegação; com benchmark, é métrica defensável. É o que separa "projeto de pesquisa" de "produto posicionável".
- **Como**: inspirar-se na estrutura do CoffeeBench (tarefas long-horizonte + agentes heterogêneos) mas com foco em **ataque/defesa**: cenários de red-team. Métricas: taxa de bloqueio correto, taxa de falso-positivo, latência de decisão, custo de overhead.
- **Esforço**: 🔴 Alto (2-4 semanas — design dos cenários, harness, baseline).
- **Retorno**: 🚀 Altíssimo — vira o argumento de venda/posicionamento central.

#### M18. Transformar AutonomyLoop em Tree Search com Budget
- **O quê**: evoluir o `AutonomyLoop` (replanning linear, tenta N vezes em sequência) para um tree search com orçamento por ramo, poda e scoring, inspirado no "Agentic Tree Search" do AI-Scientist-v2 da Sakana.
- **Por quê**: o `RootOrchestrator` já tem a *forma* de árvore (`DomainBranch`, `dependencies`, `execute_branches`) mas falta a *busca*. Hoje é "tentar de novo se falhar"; deveria ser "explorar M ramos em paralelo, podar os fracos, aprofundar os promissores, respeitar um orçamento". É o que separa o esqueleto de árvore do Kabbalah de um motor de busca real.
- **Como**: cada leaf vira um nó de busca que (1) pontua o resultado, (2) pode gerar sub-nós, (3) é podado abaixo de um threshold, (4) compartilha orçamento com siblings. O `Budget Manager` (M12) vira o limitador da árvore.
- **Dependências**: M1 (leaf precisa executar de verdade pra gerar scores) e M12 (budget limita a busca).
- **Esforço**: 🔴 Alto (1-2 semanas).
- **Retorno**: 🚀 Alto — alinha o Kabbalah com a fronteira de pesquisa (Sakana) em vez de ficar atrás dela.

---

### 🧹 BLOCO 5 — HIGIENE (rápido, renova credibilidade)

#### M13. Remover `openclaude/` (repo clonado não integrado)
- **Status 2026-07-04**: ✅ feito na Onda 4. O diretório local foi removido após verificação de zero referências no runtime/testes/bridge/setup.
- **Por quê**: não é usado pelo runtime, é risco de supply-chain, aumenta peso do repo. Auditoria 2026-04-11 Medium #14.
- **Esforço**: 🟢 10 minutos.

#### M14. Corrigir ou Remover a CLI Quebrada
- **Status 2026-07-04**: ✅ feito na Onda 4. `python -m kabbalah.cli --help` e o entrypoint `kabbalah --help` retornam exit 0.
- **Estado atual**: `src/kabbalah/cli.py` existe, contém `main()` e o entrypoint do `setup.py` funciona.
- **Esforço**: 🟢 1 dia para validação/ajustes pequenos.

#### M15. Acertar o README e Remover Relatórios Falsos
- **Status 2026-07-04**: ✅ feito na Onda 4. README atualizado, links relativos validados, relatórios antigos de status/fase arquivados ou removidos quando duplicados.
- **O quê**: relatórios antigos "APPROVED FOR PRODUCTION" e documentos de fase na raiz não são fonte de verdade.
- **Por quê**: credibilidade. Qualquer reviewer técnico foi enganado por esses docs.
- **Como**: mover ~30 relatórios de "PHASE X COMPLETE" para `docs/archive/reports/`, manter a raiz mínima e validar links do README.
- **Esforço**: 🟢 2-3 horas.

#### M16. Tirar MockProvider do Export Público
- **Status 2026-07-04**: ✅ feito na Onda 4. `MockProvider` e `MockResponseType` continuam disponíveis em `kabbalah.providers.mock_provider`, mas não são exportados por `kabbalah.providers`.
- **O quê**: remover `MockProvider` de `providers/__init__.py:__all__`.
- **Por quê**: roadmap proíbe mock em runtime; exportá-lo publicamente é governance mismatch. Mantenha o arquivo, mas não exporte.
- **Esforço**: 🟢 5 minutos.

---

## PARTE 7 — ROADMAP SUGERIDO (90 dias)

### Sprint 1 (semanas 1-2): "Provar que funciona"
- **M1** Conectar LeafNode ao Provider
- **M2** Consertar Fallback de Memória
- **M13** Remover `openclaude/`
- **M14** Validar/ajustar CLI existente
- **M15** Acertar README + arquivar relatórios
- **M16** Tirar MockProvider do export

→ **Resultado**: um demo ponta-a-ponta real (input → leaf → provider → output) com kernel de controle no meio. Repo honesto.

### Sprint 2 (semanas 3-4): "Fechar a segurança"
- **M4** ✅ Normalização/evasão básica aplicada na Wave 3; manter testes e evoluir para M11
- **M5** RBAC deny-by-default
- **M6** Log no enforcement path
- **M7** ✅ Contratos em SQLite aplicados na Wave 2; evoluir índice/assinatura/relatórios

→ **Resultado**: kernel de controle sem buracos óbvios. Auditável.

### Sprint 3 (semanas 5-8): "Features visíveis + valor mensurável"
- **M3** Gateway canônico unificado
- **M8** Model Comparison (rouba UX do Odysseus)
- **M9** Orquestração como Group Chat no ST
- **M12** Budget Manager (libera M18)

→ **Resultado**: demo matadora. O kernel aparece como valor, não como código invisível.

### Sprint 4 (semanas 9-12): "Robustez + fronteira de pesquisa"
- **M10** Sandbox real (E2B)
- **M11** Classificador ML no Qlipot
- **M17** Kabbalah-Bench (benchmark de governance) ← **inicia aqui, é longo**
- **M18** Tree Search com Budget (avanço de pesquisa, alinha com Sakana)

→ **Resultado**: pronto pra posicionar como "MCP security gateway" maduro **e** com benchmark defensável que prova o valor em números.

---

## PARTE 8 — POSICIONAMENTO ESTRATÉGICO

### A tese

O mercado em 2026 está **lotado de frontends e workspaces** (SillyTavern, Odysseus 69k★, Open WebUI 136k★) e **vazio em governance**. O Odysseus tem agentes autônomos que rodam bash/files/web **sem nenhuma camada de controle**.

**O movimento do Kabbalah não é competir com eles. É ser o piso de segurança que eles precisam** (e ainda não sabem que precisam).

### Onde o Kabbalah é genuinamente singular

> É um **policy/governance kernel para agentes**, não um orquestrador de fluxo. A maioria dos concorrentes foca em *como fazer os agentes trabalharem juntos*; o Kabbalah foca em *como autorizar, auditar e conter cada ação perigosa antes que ela execute*.

Diferenciais honestos:
1. **Pipeline de decisão pré-execução completo** (intenção → RBAC+contrato+risco → HITL → execução). Poucos projetos open source têm isso encadeado e testado.
2. **HITL fail-safe by default** — sem provider de aprovação, alto risco fica pendente, não auto-aprovado.
3. **Contratos entre agentes** — ideia incomum, aproxima agentes de transações com trust.
4. **Aprendizado federado local** (SyncHub) — visão de rede de instâncias que aprendem juntas.
5. **Memória temporal de risco** — Qlipot usa histórico de ações pra elevar suspeição.

### O paradoxo virtuoso

> A camada de CONTROLE está mais madura que a de LLM. Isso é o **inverso** da maioria dos projetos — onde constroem o agente inteligente primeiro e pensam em segurança depois.

A decisão de focar controle enquanto a equipe de LLM esteve parada foi **estratégica e acertada**. O resultado: o diferencial (governance) está pronto; falta o commodity (chamar LLM — que todo mundo sabe fazer). **Fechar a lacuna LLM é o trabalho mais fácil do projeto.**

---

## APÊNDICE — Fontes e Evidências

Todas as claims deste doc são verificáveis no repositório:

- **Volume histórico do documento original**: contagem Python em `src/` (52 arquivos, ~15.3k linhas) e `tests/` (66, ~24.6k).
- **Volume atual verificado em 2026-07-04**: `src/kabbalah/` com 53 arquivos/~15.807 linhas; `tests/` com 69 arquivos/~24.994 linhas; `kabbalah_mcp_bridge.py` com 833 linhas.
- **Estado histórico dos testes**: `docs/audit/FORENSIC_AUDIT_2026-04-11.md` (812 passed / 74 failed / 4 skipped). Não usar esse número como estado atual.
- **Estado atual de hardening focal**: 64 testes passaram no conjunto `test_bridge_hardening_wave1`, `test_bridge_hardening_wave2`, `test_qlipot_hardening_wave3`, `test_contrato_store`, `test_cofre` e `test_sillytavern_mcp_bridge`.
- **Estado atual da suíte completa**: `pytest tests -q → 1127 passed, 89 skipped`.
- **Hardening Qlipot Wave 3**: `src/kabbalah/qlipot.py` contém normalização NFKC/casefold, remoção de chars invisíveis, homoglyphs parciais, scan de base64, padrões críticos e `aplicar_correcao()` com origem autorizada/clamp/audit.
- **Contratos persistentes Wave 2**: `src/kabbalah/contrato_store.py` + `src/kabbalah/contratos.py`.
- **Leaf mudo**: `src/kabbalah/domain_orchestrator.py:215-236`.
- **Gateway órfão**: varredura de imports em todo `src/` (zero referências externas a `LLMGateway`).
- **CLI validada**: `setup.py` aponta para `kabbalah.cli:main`; `python -m kabbalah.cli --help` e `kabbalah --help` funcionam.
- **openclaude arquivado/removido**: o diretório local não integrado foi removido na Onda 4 após verificação de zero referências.
- **Origem do código**: `docs/audit/LAUDO_PERICIAL_ANTIGRAVITY.md`, `docs/audit/PERICIA_CIRURGICA_CODEX_2026_04_07.md`, `.kiro/specs/`.
- **Comparativos de mercado**: `odysseusai.dev`, `docs.sillytavern.app`, `docs.cognee.ai`, `sakana.ai`, `github.com/sakanaai` (AI-Scientist-v2, CoffeeBench, ShinkaEvolve, continuous-thought-machines, evolutionary-model-merge).

---

**Fim do documento.**
