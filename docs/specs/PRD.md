# Kabbalah — Product Requirements Document (PRD)

> **Versão**: 1.0 · **Data**: 2026-07-06 · **Status**: validado contra o código
> em `wave-11-federated` · **Autor**: consolidado por IA sob direção de
> Charles Nóbrega.
>
> **Lugar deste documento na hierarquia** (ver `docs/ops/context-pack.md`): este
> PRD é o guarda-chuva de **produto** (o *quê* e o *porquê*). Ele **não substitui**
> nem compete com as fontes canônicas:
> - Execução / progresso real: `docs/roadmap/handoff-execution-plan.md` (**vence**
>   em qualquer divergência de progresso).
> - Arquitetura: `docs/ARCHITECTURE.md`.
> - Critérios de aceite em formato EARS: `docs/specs/requirements.md` (nota: esse
>   arquivo é de 2026-04-06 e ainda é **aspiracional** — ver §14 "Divergências").
> Este PRD reconcilia a visão de produto com o **estado real do código**, validado
> em 2026-07-06.

---

## 0. Estado validado nesta redação (evidência, não claim)

Tudo abaixo foi verificado diretamente no repositório em 2026-07-06, branch
`wave-11-federated`, working tree limpo:

| Item | Valor validado | Como foi verificado |
|---|---|---|
| Versão | `0.8.0` (alpha) | `src/kabbalah/__init__.py` + `pyproject.toml` classifiers `3 - Alpha` |
| Suíte de testes | **1239 passed, 89 skipped, 0 failed** em 126,85s | `.venv\Scripts\python.exe -m pytest tests -q` executado nesta sessão |
| Arquivos de teste | 83 | `find tests -name test_*.py` |
| Funções `def test_` | 1309 | grep no diretório `tests` |
| Módulos runtime | ~60 arquivos `.py` / ~18.358 LOC | `find src -name *.py \| wc -l` |
| Providers no registry | 11 (sem Anthropic direto — via OpenRouter) | `src/kabbalah/providers/factory.py:51-61` |
| Comandos CLI | `setup`, `parse`, `config {list,add-key,remove-key,test-key,set-budget,set-routing,set-network,trust-add,trust-remove}`, `status`, `version` | `src/kabbalah/cli.py` |
| RiskAssessor plugável (Onda 10.2/M11) | **implementado** em `src/kabbalah/risk_assessor.py` | protocolo + heurística + assessor LLM presentes; commit `8cdcbf5` |
| Sandbox Docker (Onda 10.1/M10) | implementado, opt-in (`KABBALAH_USE_DOCKER_SANDBOX=1`, default OFF) | `execution_engine.py`; handoff §3 Onda 10.1 |
| Federação SyncHub (Onda 11) | bundles assinados Ed25519, offline | `sync_hub.py`; `tests/test_sync_hub_federation.py` |
| Skips | 89 constantes = testes live de providers, desligados por política | esperado, **não é bug** |

---

## 1. Sumário executivo

### Elevator pitch

> **Kabbalah é o runtime de contenção para agentes de IA.** Enquanto LangChain,
> CrewAI e Sakana focam em fazer o agente *conseguir mais*, o Kabbalah decide, a
> cada ação e **antes de executar**, se ela *pode* rodar: pontuação de intenção,
> contrato, autorização RBAC, aprovação humana e orçamento — com trilha de
> auditoria imutável. É o firewall + antivírus + caixa-preta que um agente
> confiável roda por baixo. E prova sua eficácia em números (Kabbalah-Bench),
> não em promessa.

**Kabbalah é um kernel de governança zero-trust para agentes de IA.** Ele se
posiciona entre a UI/cliente de um agente e as ações que esse agente quer
executar, e aplica — **antes de qualquer execução** — pontuação de intenção,
contratos, autorização RBAC, aprovação humana, acesso a segredos, controle de
orçamento e persistência auditável.

O alvo de frontend atual é o **SillyTavern** via seu cliente MCP. O Kabbalah roda
como servidor MCP stdio (`kabbalah_mcp_bridge.py`) e expõe *tools* guardadas em
vez de deixar um agente de chat chamar sistema de arquivos, shell, rede, banco ou
providers diretamente.

**É software alpha.** O kernel de segurança, o bridge, a CLI, o registry de
providers, o ledger de orçamento, o profiler de hardware e a suíte de testes estão
implementados e verdes. Os limites alpha (orquestração raiz sequencial por padrão,
federação local fase-1, chaves reais fornecidas por instalação) estão documentados
e são intencionais.

**Diferencial de produto**: enquanto a maioria dos frameworks de agente foca em
*capacidade* (fazer o agente conseguir mais coisas), o Kabbalah é um produto de
*contenção* — o valor está em **negar corretamente** ações perigosas e em provar
essa contenção com números (Kabbalah-Bench), mantendo falso-positivo baixo.

---

## 2. Problema e motivação

Agentes de IA com acesso a ferramentas (shell, arquivos, rede, banco, providers
LLM) são poderosos e perigosos na mesma medida. Os riscos concretos:

1. **Execução destrutiva**: `rm -rf`, sobrescrita de arquivos, comandos com
   escalada de privilégio.
2. **Exfiltração**: leitura de segredos e envio para fora (base64, requests a
   destinos privados/loopback).
3. **Prompt injection / evasão**: unicode, homoglyphs, zero-width, base64,
   sinônimos, para burlar filtros ingênuos.
4. **Custo descontrolado**: chamadas a providers pagos sem teto por run/dia.
5. **Ausência de trilha de auditoria**: impossível reconstruir *quem/qual
   agente* fez *o quê* e *por quê* foi permitido.
6. **Independência do julgador**: se o modelo que *julga* o risco é do mesmo
   fornecedor do modelo *julgado*, a independência é ilusória.

O Kabbalah ataca cada um desses pontos com um pipeline fail-closed e persistência
append-only, e mede a eficácia com um benchmark de contenção dedicado.

---

## 3. Visão de produto e proposta de valor

**Visão**: ser a camada de governança padrão — o "firewall + antivírus + trilha
de auditoria" — para qualquer agente de IA que execute ações no mundo real,
começando pelo ecossistema MCP/SillyTavern e generalizável a qualquer cliente MCP.

**Proposta de valor por público**:

- **Para um time de dev**: bridge MCP fail-closed, contratos agente-a-agente com
  contadores persistidos e eventos append-only, scoring de intenção endurecido,
  tickets HITL, acesso a segredos via cofre, roteamento de providers com budget e
  fallback, e uma CLI para setup/config/status seguros.
- **Para um operador de segurança/compliance**: deny-by-default, aprovação humana
  explícita (pendente ≠ aprovado), auditoria imutável, e um benchmark que
  quantifica taxa de contenção e falso-positivo.
- **Para pesquisa**: Kabbalah-Bench (contenção red-team declarativa), autonomy
  loop com tree search opcional, e federação de "definições de ameaça" assinadas
  (modelo antivírus, não rede social).

---

## 3.5 Linhagem intelectual e tecnologias estudadas

> Fonte no repo: `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md` §5 (análise **não
> canônica** — usa-se aqui só o que virou decisão/implementação) + handoff §9.
> O Kabbalah **não é fork** de Sakana/LangGraph/CrewAI (único autor dos commits é
> o Charles; código gerado por IAs de codificação sob direção humana). A relação
> com essas referências é de **posicionamento e benchmark**, não de cópia de
> arquitetura.

**Tese central**: as referências de fronteira (Sakana, AI-Scientist) focam na
*inteligência/autonomia* do agente; o Kabbalah foca na *contenção*. São
complementares, não concorrentes — *"um agente inteligente sem kernel de
contenção é perigoso; um kernel sem agentes é vazio"*.

| Referência estudada | O que é | O que virou no Kabbalah (estado validado) |
|---|---|---|
| **Sakana CoffeeBench** | benchmark de economias multi-agente heterogêneas (ataque/defesa) | **Kabbalah-Bench** — contenção red-team declarativa (`benchmarks/run.py` + results datados) [Impl. Onda 9.1] |
| **Sakana AI-Scientist-v2** ("Agentic Tree Search") | decompor → explorar ramos → podar → aprofundar | **AutonomyLoop tree mode** (`KABBALAH_SEARCH_MODE=tree`, budget por ramo, poda) [Impl. Onda 9.2] |
| **Sakana evolutionary-model-merge** | merge de modelos por evolução | Aspiracional: além de selecionar provider (LLMGateway), merjar capacidades [não implementado — fronteira] |
| **Odysseus AI** (odysseusai.dev) | workspace self-hosted com agentes autônomos rodando bash/files/web **sem camada de governança** | Posicionamento: "o Kabbalah é a camada que falta no Odysseus"; inspirou **Model Comparison** (`compare_models`, UX side-by-side) [Impl. Onda 8.1]. Insumo analisado em `E:\projetos\odysseus-analysis` |
| **Cognee / Mem0** | memória semântica vetorial | Backend de memória opcional (extra `memory`); fallback JSONL [Parcial] |
| **MCP (Model Context Protocol)** | padrão de tools para LLM | Todo o `kabbalah_mcp_bridge.py` [Impl.] |
| **SillyTavern** | frontend de chat multi-personagem | Alvo de frontend atual via cliente MCP [Impl.] |

### Posicionamento de mercado

| Ferramenta | Foco primário | Governança de execução |
|---|---|---|
| LangChain / LangGraph | conectar LLM + tools / DAG | mínima |
| CrewAI | times de agentes colaborativos | mínima |
| AutoGen | conversação multi-agente | mínima |
| Sakana (AI-Scientist, CoffeeBench) | inteligência/evolução do agente | fora do foco |
| Odysseus / Open WebUI | workspace self-hosted | nenhuma |
| **Kabbalah** | **contenção / governança zero-trust** | **produto central** |

O mercado 2026 está saturado em *frontends* e *workspaces* e quase vazio em
*governance de ação* — a lacuna que o Kabbalah ocupa.

---

## 4. Personas e usuários-alvo

| Persona | Objetivo | Como o Kabbalah serve |
|---|---|---|
| **Operador de agente (SillyTavern)** | Rodar agentes de chat que executam tools sem se expor a ações destrutivas | Bridge MCP com tools guardadas; contratos e HITL no meio |
| **Dev de integração MCP** | Plugar governança em um cliente MCP próprio | Servidor stdio JSON-RPC + tools documentadas + env vars de política |
| **Operador de segurança / compliance** | Provar contenção e ter trilha auditável | RBAC deny-by-default, auditoria append-only, Kabbalah-Bench |
| **Pesquisador de segurança de agentes** | Medir/comparar contenção; estudar evasões | Benchmark declarativo, tree search, RiskAssessor plugável e independente |
| **Charles (owner)** | Sistema limpo, instalável em 5 min, honesto sobre limites | README-vitrine, quickstart validado, mensagens de erro acionáveis |

Premissa de ambiente atual: **rede confiável, sem clientes não confiáveis** (o
kernel protege contra o *agente*, não ainda contra um adversário de rede completo).

---

## 5. Casos de uso principais (fluxos)

### UC-1 — Chamada de tool guardada (fluxo canônico)
Cliente MCP chama uma tool → Bridge → `Qlipot.avaliar_intencao` (score + contexto
temporal) → `FirewallMCP.autorizar` (RBAC deny-by-default + `Contratos.verificar_detalhado`
+ score) → se exige humano: cria ticket HITL e devolve `HITL_REQUIRED`; se negado:
`POLICY_DENIED`; se permitido: executa a ação constrita e devolve JSON. Toda decisão
é auditada.

### UC-2 — Contrato agente-a-agente
`propose_contract` (com `papeis=["coordinator"]`) → `sign_contract` → tool alvo.
Contratos são **obrigatórios por padrão** para tools não-bootstrap. Contadores
(`max_calls`) são consumidos atomicamente; violações e eventos vão para
`contrato_eventos` (append-only).

### UC-3 — Run governado com provider real
`kabbalah parse` gera uma `Specification` (run_id). Root → Domain → Leaf; **com um
`LLMGateway` injetado**, o leaf tenta candidatos de provider ordenados (cheap-first
com escalada), devolve `llm_response` como artifact e grava consumo no
`BudgetLedger`. **Sem gateway injetado**, o leaf devolve `status="skipped"`
explícito — nunca `success` falso.

### UC-4 — Setup por instalação (sem segredo no repo)
`kabbalah setup` lista providers, pede chaves com input oculto (`getpass`), valida
cada uma com uma chamada de teste e só então guarda no keyring do SO. Nenhum
segredo em arquivo tracked, state DB, log ou stdout.

### UC-5 — Comparação de modelos
`compare_models` despacha a mesma task a N providers pelo pipeline de autorização
normal e devolve linhas (provider, modelo, latência, tokens, custo, resposta,
erro). Respeita gateway, budget e disponibilidade real. Mock só sob
`KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.

### UC-6 — Benchmark de contenção
`python -m benchmarks.run` roda cenários red-team declarativos contra o pipeline
real e mede contenção correta vs falso-positivo, com relatório datado em
`benchmarks/results/`.

### UC-7 — Federação de correções (SyncHub fase 2)
Bundles de sinapses assinados Ed25519: verificação de assinatura → publicador na
trust list → quarentena → quórum → clamp ±0.30 → `aplicar_correcao(origem="sync_hub")`
→ auditoria. Modos `off` (default) / `receber` / `receber+contribuir`. Nunca
conteúdo bruto sai da máquina.

---

## 5.5 Histórias de usuário (com critério de aceite)

> Cada critério de aceite abaixo aponta para comportamento **validado no código**
> (arquivo:linha), não para intenção.

- **US-01 — Gate de governança fail-closed.** Como operador de segurança, quero
  que toda tool não-bootstrap passe por Qlipot → RBAC deny-by-default → contrato
  antes de executar, para que nenhuma ação escape do kernel.
  *Aceite*: `FirewallMCP` sem checker nega (`firewall_mcp.py:143-144`); tool sem
  contrato ativo → `POLICY_DENIED`; decisão registrada em auditoria.
- **US-02 — Aprovação humana explícita.** Como compliance, quero que ações
  sensíveis exijam ticket HITL e que "pendente" nunca conte como aprovado.
  *Aceite*: sem provider de aprovação, `aprovado=False` / `PENDING` (`hitl.py:86-87`);
  execução só após aprovação explícita; `check_hitl_status` exposto no bridge.
- **US-03 — Teto de custo por run/dia/provider.** Como DevOps de IA, quero limitar
  gasto e abortar no modo `block`.
  *Aceite*: `KABBALAH_BUDGET_MODE=block` levanta `BudgetExceededError` ao estourar
  (`budget_manager.py:212-213`); `warn` registra e segue; toda chamada grava no
  `BudgetLedger` append-only.
- **US-04 — Sandbox de ferramentas.** Como security engineer, quero shell desligado
  por padrão e destinos de rede privados bloqueados.
  *Aceite*: `execute_command` só com `KABBALAH_BRIDGE_ENABLE_SHELL=1`; arquivos
  restritos a `KABBALAH_BRIDGE_ALLOWED_DIRS`; loopback/privado bloqueado salvo
  `ALLOW_PRIVATE_NETWORKS=1` (anti-SSRF); sandbox Docker opcional.
- **US-05 — Fallback de provider.** Como DevOps de IA, quero que um provider
  indisponível caia para o próximo candidato sem derrubar a run.
  *Aceite*: falha de conexão → `mark_unavailable` + próximo candidato
  (`domain_orchestrator.py:254`); só falha ao esgotar todos; erro em metadata,
  nunca exceção que derruba a árvore.
- **US-06 — Juiz de risco independente.** Como arquiteto, quero que o avaliador de
  risco possa ser de fornecedor diferente dos modelos governados.
  *Aceite*: `LLMRiskAssessor` seleciona por `capability="risk-judge"`
  (`risk_assessor.py:206`); heurística offline como fallback; decisão carrega
  `RISK_ASSESSOR_VERSION`.
- **US-07 — Correção federada só se comprovada.** Como operador de rede, quero que
  correções importadas só entrem se assinadas, confiáveis e comprovadamente
  melhorem contenção.
  *Aceite*: bundle verificado (Ed25519) **antes** do trust-check
  (`sync_hub.py:184-188`); quarentena + quórum + clamp ±0.30; modo `off` por
  padrão; bench antes/depois exigido (Onda 11.5).

---

## 6. Escopo

### 6.1 Dentro do escopo (implementado e verde)
- Pipeline de segurança MCP: Qlipot → FirewallMCP → contratos → HITL → execução.
- Persistência SQLite para tickets HITL, contratos, eventos de contrato, ledger de
  orçamento e perfis de hardware (banco único selecionado por
  `KABBALAH_BRIDGE_STATE_DB`).
- Registry de providers, adaptador OpenAI-compatible, candidatos de fallback
  ordenados e seleção consciente de orçamento.
- Kabbalah-Bench + tree search opcional (`KABBALAH_SEARCH_MODE=tree`; default
  linear).
- SyncHub: bundles offline assinados (Ed25519, trust list, modos de rede,
  checagens de replay/tamper/versão, evidência bench antes/depois).
- CLI setup/config/status com saída JSON e manuseio seguro de segredos.
- Renderer de eventos de group-chat SillyTavern + exemplo Blank Card.
- Sandbox Docker opt-in (Onda 10.1); RiskAssessor plugável independente (Onda 10.2).

### 6.2 Fora do escopo agora (limites alpha declarados)
- Orquestração raiz **não** injeta `LLMGateway` por padrão (o caminho existe e é
  testado; o default raiz é sequencial e sem gateway).
- Federação é troca de bundles assinados offline; **sem** hub HTTPS nem gossip P2P
  (fases 3 e 4, futuras).
- Chamadas LLM reais exigem credenciais configuradas fora do código-fonte.
- Fit de modelo local é heurística/profiler, **não** um sistema de auto-deploy.
- Sandbox Docker é barreira **moderada** (compartilha kernel do host, escrita no
  dir montado) — adequada a teste controlado, não à prova de agente hostil em
  produção.

### 6.3 Não-objetivos (decisões arquiteturais)
- **Sem** scraper/engenharia reversa de serviços sem API oficial embutido no
  kernel (ex.: Suno só via MCP server de terceiro, como tool governada).
- Providers vs tools: o que *raciocina* (texto→texto/estrutura) é provider via
  gateway; o que *gera artefato ou executa ação* (áudio, imagem, vídeo, e-mail,
  comando) é **tool** via pipeline MCP. ElevenLabs/ComfyUI são tools, nunca
  providers.
- **Sem** enfraquecer defaults de segurança para fazer teste passar.

---

## 7. Requisitos funcionais por subsistema

> Nomenclatura: RF-<subsistema>-<n>. Cada RF marca [Implementado] quando validado
> no código nesta redação.

### 7.1 Kernel de segurança
- **RF-SEC-1** [Impl.] O sistema DEVE avaliar toda ação via `Qlipot` (intenção +
  contexto temporal), com hardening de unicode (NFKC, zero-width, homoglyphs),
  decodificação base64 no scoring e sinônimos pt/en. (`qlipot.py`, `risk_assessor.py`)
- **RF-SEC-2** [Impl.] `FirewallMCP` DEVE ser **deny-by-default**: sem `rbac_checker`
  configurado, nega. Permissividade só via `permitir_tudo` importável e explícito.
  (`firewall_mcp.py`)
- **RF-SEC-3** [Impl.] Exceção em verificação = **negado** (fail-closed).
- **RF-SEC-4** [Impl.] `aplicar_correcao` só com origem autorizada, clamp ±0.30 e
  auditoria; carrega `RISK_ASSESSOR_VERSION` + identidade do modelo.
- **RF-SEC-5** [Impl.] O avaliador de risco DEVE ser plugável e poder ser
  **independente do fornecedor** dos modelos governados (capability `risk-judge`);
  heurística offline como fallback. (`risk_assessor.py`)

### 7.2 Contratos
- **RF-CTR-1** [Impl.] Contratos obrigatórios por padrão para tools não-bootstrap;
  fluxo `propose → sign → tool`.
- **RF-CTR-2** [Impl.] Contadores `max_calls` consumidos **atomicamente**; estado
  persistido em SQLite (`contrato_store.py`).
- **RF-CTR-3** [Impl.] Violações e eventos em tabela **append-only**
  (`contrato_eventos`); separação explícita ausência × violação (`VerificationOutcome`).
- **RF-CTR-4** [Impl.] Sanitização de chaves de contrato (Onda 12).

### 7.3 HITL (human-in-the-loop)
- **RF-HITL-1** [Impl.] Ações que exigem aprovação criam ticket; **pendente ≠
  aprovado** (fail-safe). (`hitl.py`)
- **RF-HITL-2** [Impl.] Sem provider de aprovação → permanece pendente, nunca
  auto-aprovado. Tool `check_hitl_status` exposta no bridge.

### 7.4 Orquestração em árvore
- **RF-ORQ-1** [Impl.] `IntakeNode` valida request e gera `Specification` canônica
  com `run_id`.
- **RF-ORQ-2** [Impl.] `RootOrchestrator` decompõe em branches de domínio.
- **RF-ORQ-3** [Impl.] `DomainOrchestrator` gera leaf nodes; com `LLMGateway`
  injetado executa provider real; sem gateway, `status="skipped"` explícito.
- **RF-ORQ-4** [Impl.] Rastreio hierárquico `run_id:branch_id:leaf_id` propagado.
- **RF-ORQ-5** [Parcial] Execução paralela de domínios independentes: **o default
  raiz é sequencial** (limite alpha declarado); o caminho com gateway é testado.
- **RF-ORQ-6** [Impl.] `AutonomyLoop` com tree search opcional
  (`KABBALAH_SEARCH_MODE=tree|linear`, default `linear`).

### 7.5 Camada LLM (gateway, providers, budget, hardware)
- **RF-LLM-1** [Impl.] `LLMGateway` é o **único** seletor de provider por
  `(role, capability, budget_hint)`; `ProviderFactory` só constrói.
- **RF-LLM-2** [Impl.] Registry de capacidades por modelo (capabilities, context
  window, custo/1M tokens, licença, local|cloud, backend/quant/VRAM para locais,
  `tokens_s_medido`).
- **RF-LLM-3** [Impl.] Política **cheap-first com escalada**: local → rápido/barato
  → premium; escala por role ou por falha de contrato de sucesso.
- **RF-LLM-4** [Impl.] Fallback por candidato: conexão/instanciação falha marca
  candidato indisponível (com log) e tenta o próximo; só falha ao esgotar todos.
- **RF-LLM-5** [Impl.] `BudgetLedger` append-only (provider, modelo, tokens in/out,
  custo, trace_id, timestamp); tokens vêm do `usage` do provider, nunca `len/4`.
- **RF-LLM-6** [Impl.] `BudgetManager` com limites por run/dia/provider, modos
  `warn` (default) e `block` (`KABBALAH_BUDGET_*`); `block` levanta
  `BudgetExceededError`. Custo calculado pelo pricing do `ModelProfile` × usage
  quando o provider reporta `cost=0.0`.
- **RF-LLM-7** [Impl.] `HardwareProfiler`: detecção em 3 degraus (vendor API →
  fallback neutro → CPU-only), fingerprint com re-baseline em mudança, tiers por
  **medição** (tokens/s), persistência append-only em `hardware_profiles`; é a
  fonte canônica do `hardware_hash`.
- **RF-LLM-8** [Impl.] Providers no registry (11): `openai`, `google_gemini`,
  `groq`, `mistral`, `together`, `deepseek` (nativos) + `ollama_local`,
  `openrouter`, `groq_compatible`, `cerebras`, `sambanova` (OpenAI-compatible).
  **DeepSeek e Anthropic/Claude entram via OpenRouter** — sem provider nativo
  Anthropic por decisão de design.
- **RF-LLM-9** [Impl.] Mock só sob `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`
  (`docs/specs/NO_MOCK_RUNTIME_POLICY.md`).

### 7.6 Execução de tools (bridge)
- **RF-TOOL-1** [Impl.] Tools: `read_file`, `write_file`, `execute_command`,
  `network_request`, `read_env_var`, `call_tool`, `database_query`.
- **RF-TOOL-2** [Impl.] `execute_command` desabilitado salvo
  `KABBALAH_BRIDGE_ENABLE_SHELL=1`.
- **RF-TOOL-3** [Impl.] Arquivos/SQLite restritos a `KABBALAH_BRIDGE_ALLOWED_DIRS`.
- **RF-TOOL-4** [Impl.] `read_env_var` só retorna vars em
  `KABBALAH_BRIDGE_ENV_ALLOWLIST`.
- **RF-TOOL-5** [Impl.] Destinos privados/loopback/link-local/reservados bloqueados
  salvo `KABBALAH_BRIDGE_ALLOW_PRIVATE_NETWORKS=1` (anti-SSRF).
- **RF-TOOL-6** [Impl.] Sandbox Docker opt-in (`KABBALAH_USE_DOCKER_SANDBOX=1`,
  default OFF).
- **RF-TOOL-7** [Impl.] Logs do bridge em `stderr`; stdout reservado ao JSON-RPC MCP.

### 7.7 Cofre / segredos
- **RF-COF-1** [Impl.] Acesso a segredos via Bitwarden (`CofreBitwarden`) com
  `BITWARDEN_CLI_PATH`, `KABBALAH_BW_SHA256`, `clear_on_read`, `limpar_cache()`.
- **RF-COF-2** [Impl.] Cofre dinâmico de segredos (Onda 12); segredos nunca em
  código, log ou state DB.

### 7.8 Memória
- **RF-MEM-1** [Impl.] `MemorySubsystem` com Cognee opcional; fallback JSONL local.
- **RF-MEM-2** [Impl.] `SQLiteVectorBackend` local lazy-init
  (`KABBALAH_USE_SQLITE_VECTOR=1`).
- **RF-MEM-3** [Impl.] `MemoryGovernance` para controle de acesso por role +
  auditoria.

### 7.9 Federação (SyncHub)
- **RF-FED-1** [Impl.] Identidade Ed25519 gerada no `kabbalah setup`; chave pública
  = identidade da instância; `hardware_hash` é telemetria, não identidade.
- **RF-FED-2** [Impl.] Bundles assinados com sinapse = `hash(assinatura_acao)`,
  delta, contadores, janela temporal grosseira, `RISK_ASSESSOR_VERSION`.
- **RF-FED-3** [Impl.] Importação com trust list + quarentena + quórum + clamp; só
  internaliza se versão do assessor for compatível.
- **RF-FED-4** [Impl.] Modos `off` (default) / `receber` / `receber+contribuir`;
  gestão via `kabbalah config set-network|trust-add|trust-remove`.

### 7.10 CLI e onboarding
- **RF-CLI-1** [Impl.] Comandos: `setup`, `parse`, `config {list,add-key,remove-key,
  test-key,set-budget,set-routing,set-network,trust-add,trust-remove}`, `status`,
  `version`.
- **RF-CLI-2** [Impl.] `kabbalah status` = painel único (hardware ativo, saúde das
  chaves sem valores, gasto do dia, contratos ativos, tickets HITL); flag `--json`
  em todo comando.
- **RF-CLI-3** [Impl.] Erros no formato **o que aconteceu → por quê → o que fazer**
  (`what_happened/why/what_to_do`); exit codes documentados
  (`docs/specs/cli-exit-codes.md`).
- **RF-CLI-4** [Impl.] Nunca pedir segredo em execução autônoma; input de segredo
  só em sessão humana interativa.

### 7.11 Observabilidade
- **RF-OBS-1** [Impl.] Trace IDs hierárquicos + logging estruturado
  (`observability/`, `trace_id_tracking.py`).
- **RF-OBS-2** [Impl.] Exporters OpenTelemetry/Prometheus no extra
  `observability`.

### 7.12 Benchmark
- **RF-BEN-1** [Impl.] Kabbalah-Bench: cenários red-team declarativos rodados contra
  o pipeline real; métricas de contenção, falso-positivo, latência de decisão;
  relatórios datados em `benchmarks/results/`.

---

## 8. Requisitos não-funcionais (reconciliados com a realidade)

- **Segurança**: fail-closed em todo o pipeline; RBAC deny-by-default; auditoria
  append-only imutável; segredos nunca em código/log/state DB; anti-SSRF; unicode
  hardening. [Estado: implementado e testado]
- **Confiabilidade**: fallback por candidato de provider; degradação graciosa sem
  Cognee; SQLite com conexão curta + busy_timeout (Windows-safe). [Impl.]
- **Portabilidade**: Windows 11 é o ambiente primário validado; CI roda
  Windows+Ubuntu (Python 3.10 e 3.11 após drop do 3.9). [Impl.]
- **Manutenibilidade**: `ruff` (`E/W/F/I/B`) verde; docstrings/type hints nos
  módulos públicos; `pyproject.toml` PEP 621 single-source de versão. [Impl.]
- **Performance**: sem SLA formal validado nesta fase; as metas de "≤30s decomposição
  / ≤60s síntese / 10+ leafs paralelos" do `requirements.md` são **aspiracionais**
  e não medidas (orquestração raiz é sequencial). [Aspiracional — ver §14]

---

## 9. Modelo de dados e persistência

- **Banco único** por bridge: `KABBALAH_BRIDGE_STATE_DB` (default
  `.kabbalah_bridge_state.sqlite3`).
- **Tabelas**: `hitl_tickets`, `contratos`, `contrato_eventos` (append-only),
  `budget_ledger` (append-only), `hardware_profiles` (append-only), + stores de
  Qlipot/SyncHub (Onda 12).
- **Padrão de referência para novo store SQLite**: `contrato_store.py` (lock +
  conexão por operação + `busy_timeout` + tabela de eventos append-only para
  auditoria). Nenhum módulo cria seu próprio arquivo SQLite avulso.
- **Modelos de domínio** (`models.py`): `UserRequest`, `Specification`
  (`run_id`, domínios, dependências, `version`, `translation_info`, `created_at`).

---

## 10. Superfície de interface (contratos externos)

### 10.1 Tools do bridge MCP
`read_file`, `write_file`, `execute_command`, `network_request`, `read_env_var`,
`call_tool`, `database_query`, `check_hitl_status`, `propose_contract`,
`sign_contract`, `reject_contract`, `complete_task`, `get_network_stats`,
`get_budget_stats`, `get_config_status`, `compare_models`, `render_group_event`.

### 10.2 Variáveis de ambiente de política (principais)
`KABBALAH_BRIDGE_STATE_DB`, `KABBALAH_BRIDGE_ENABLE_SHELL`,
`KABBALAH_BRIDGE_ALLOWED_DIRS`, `KABBALAH_BRIDGE_ENV_ALLOWLIST`,
`KABBALAH_BRIDGE_ALLOW_PRIVATE_NETWORKS`, `KABBALAH_BUDGET_*`,
`KABBALAH_BUDGET_MODE`, `KABBALAH_SEARCH_MODE`, `KABBALAH_USE_DOCKER_SANDBOX`,
`KABBALAH_USE_SQLITE_VECTOR`, `KABBALAH_ALLOW_TEST_FAKE_PROVIDER`,
`BW_SESSION/BW_EMAIL/BW_PASSWORD`, `BITWARDEN_CLI_PATH`, `KABBALAH_BW_SHA256`.

### 10.3 Empacotamento
Pacote `kabbalah` (src-layout), entrypoint `kabbalah = kabbalah.cli:main`, extras
`mcp`, `memory`, `observability`, `dev`, `docs`. `requirements-*.txt` mantidos
como espelhos.

---

## 11. Métricas de sucesso / KPIs

| KPI | Alvo | Fonte de medição |
|---|---|---|
| Taxa de contenção correta | ≥ baseline registrado, crescente | Kabbalah-Bench |
| Falso-positivo (cenários benignos) | não aumentar ao evoluir o assessor | Kabbalah-Bench (cenários de controle obrigatórios) |
| Suíte verde | 0 failed sempre; skips = 89 constantes | `pytest tests -q` |
| Tempo de instalação → demo | ≤ 5 min a partir do README, sem perguntar | quickstart validado em clone limpo |
| Segredos vazados em artefato tracked/log/stdout | 0 | hook gitleaks + `config list` sem valores |
| Custo por run/dia | dentro dos limites configurados | `BudgetLedger` + `get_budget_stats` |
| Federação só promove correção que melhora contenção | 100% | bench antes/depois (Onda 11.5) |

---

## 12. Estado de validação atual

- **Testes**: 1239 passed, 89 skipped, 0 failed (2026-07-06, `wave-11-federated`).
- **Lint**: `ruff` verde (`E/W/F/I/B`) por histórico recente; working tree limpo.
- **Ondas 1–9, 11, 10.1, 10.2**: implementadas e testadas (ver §0 e handoff plan).
- **Skips**: testes live de providers, desligados por política — estado esperado.

---

## 13. Roadmap (resumo — fonte canônica é o handoff plan)

- **Ondas 1–3**: hardening (bridge, contratos SQLite, unicode/regex/base64). ✅
- **Onda 4**: higiene do repo. ✅
- **Onda 5**: fechar o loop LLM (gateway canônico, adaptador OpenAI-compat, leaf
  conectado, ledger, hardware profiler). ✅ (a mais importante)
- **Onda 6**: RBAC deny-by-default + log no enforcement. ✅
- **Onda 7**: BudgetManager (limites, modos, fallback, custo real no ledger). ✅
- **Onda 8**: features visíveis + acabamento (compare_models, group chat, CLI,
  packaging, CI, docs-vitrine). ✅
- **Onda 9**: Kabbalah-Bench + tree search. ✅
- **Onda 10.1**: sandbox Docker opt-in. ✅ · **Onda 10.2**: RiskAssessor plugável
  independente. ✅ no código (checkbox do plano defasado — ver §14).
- **Onda 11**: federação SyncHub fase-2 (bundles assinados offline). ✅
- **Onda 12**: hardening físico (secrets vault dinâmico, sandbox, SQLite vector,
  persistência Qlipot/SyncHub, time locks UTC, sanitização de chave). ✅ no código.
- **Futuro (não especificar agora)**: federação fase 3 (hub HTTPS opt-in) e fase 4
  (P2P gossip); endurecimento do sandbox; guarda de VRAM em runtime.

---

## 14. Divergências encontradas na validação (ação recomendada)

Estas são inconsistências **entre documentos e código** achadas ao "validar tudo".
Nenhuma é bug de runtime — são dívidas de documentação/reconciliação:

1. **Onda 10.2 marcada como pendente `[ ]`** no `handoff-execution-plan.md` §3,
   mas `src/kabbalah/risk_assessor.py` implementa o `RiskAssessor` plugável e há
   commit `8cdcbf5 feat(wave10): implement pluggable independent RiskAssessor`.
   → **Ação**: marcar 10.2 como concluída no handoff plan (ou registrar o que
   falta, se algo do design não foi coberto).
2. **Onda 12 sem seção no plano canônico**: o `handoff-execution-plan.md` termina
   nas Ondas 10/11, mas a Onda 12 existe no código (`test_wave12_hardening.py`,
   commit `6c8c350`) e no `context-pack.md`. → **Ação**: adicionar seção Onda 12
   ao handoff plan para o plano continuar sendo a fonte de verdade.
3. **`docs/specs/requirements.md` (v1.0, 2026-04-06) é aspiracional e não
   reconciliado**: afirma 12 providers incluindo **Anthropic nativo**, execução
   **paralela**, Cognee-first e "single binary". A realidade validada: 11
   providers sem Anthropic direto (via OpenRouter), orquestração raiz **sequencial**
   por padrão, Cognee **opcional**, distribuição via pip. → **Ação**: adicionar
   nota de topo em `requirements.md` situando-o como spec histórica/EARS, com
   ponteiro para este PRD e o handoff plan.
4. **Classifier de Python defasado**: `pyproject.toml` lista
   `Programming Language :: Python :: 3.9` e `3.12`, mas `requires-python = ">=3.10"`
   e a CI removeu 3.9 (commit `100e699`). → **Ação**: remover o classifier 3.9.
5. **Números de teste divergentes entre docs**: README cita "1229"/"1206",
   context-pack "1234", execução fresca "1239". Esperado (a suíte cresce), mas o
   PRD/README devem citar sempre o número validado mais recente.
6. **`ProviderConfigurationManager` órfão**: `providers/config.py` implementa um
   seletor de provider paralelo (modos unified/explicit/hierarchy/hybrid) que
   chama a `ProviderFactory` **direto**, contra a decisão canônica "a factory
   nunca é chamada fora do gateway". O grep confirma que só é usado por
   `providers/__init__.py` (export) e por testes — **nenhum caminho de runtime o
   consome**. → **Ação**: deprecar/remover (disciplina ponytail/YAGNI); manter
   `LLMGateway` + `configuration_manager.py` como únicos.
7. **`google-generativeai==0.3.0` pinado numa versão antiga** (`pyproject.toml:50`).
   → **Ação**: atualizar para a linha atual e revalidar `GoogleGeminiProvider`
   contra a nova API. (Único ponto onde a análise web externa acertou.)
8. **`shell=True` presente porém gated** (`execution_engine.py:532,592`): o path
   existe, mas `execute_command` é opt-in (`ENABLE_SHELL=1`) e há sandbox Docker
   opcional. Não é "aberto", mas o endurecimento (rede off, read-only, non-root,
   limites) é TODO declarado. → **Ação**: endurecer o wrapper Docker quando a fase
   física validar o caminho.

> **Status 2026-07-06**: itens 1–2 executados (handoff plan reconciliado: 10.2
> marcado com evidência, Onda 12 registrada, decisões pendentes §6 atualizadas).
> Itens 3–8 orquestrados como **Onda 13** do handoff plan, prontos para qualquer
> IA executora sob as regras da §2 daquele documento.

---

## 14.5 Plano de ação de dívida técnica (ordenado por risco × esforço)

> Nenhum item bloqueia runtime hoje; todos cabem na disciplina ponytail
> (reuso/edição do canônico, sem criar código/doc novo).
> **Status 2026-07-06**: orquestrados como **Onda 13** em
> `docs/roadmap/handoff-execution-plan.md` (13.1=DT-4 restante, 13.2=DT-2,
> 13.3=DT-1, 13.5=DT-3, + 13.4 bench risk-judge). A parte de reconciliação do
> DT-4 (plano de ondas) já foi executada nesta data.

| # | Item | Origem | Risco | Esforço | Ação |
|---|---|---|---|---|---|
| DT-1 | `google-generativeai==0.3.0` | `pyproject.toml:50` | Médio-alto (SDK antigo) | Baixo | Atualizar para linha atual + revalidar provider Gemini |
| DT-2 | `ProviderConfigurationManager` órfão | `providers/config.py` | Baixo (fora do runtime) mas fere decisão canônica | Baixo | Deprecar/remover; deixar `LLMGateway` + `configuration_manager.py` |
| DT-3 | `shell=True` não endurecido | `execution_engine.py:532,592` | Médio (gated, barreira fraca se ativado) | Médio | Endurecer sandbox Docker (rede off, read-only, non-root, limites) |
| DT-4 | Docs canônicos defasados | handoff §3 · `requirements.md` · `pyproject` | Baixo (só doc) | Baixo | Marcar Onda 10.2; add seção Onda 12; nota de topo em `requirements.md`; remover classifier 3.9 |

**Ordem recomendada**: DT-4 (reconciliação, destrava clareza) → DT-2 (limpeza
YAGNI) → DT-1 (dependência) → DT-3 (endurecimento, pós fase física).

---

## 15. Premissas e restrições

- **Premissas**: providers LLM disponíveis quando configurados; chaves fornecidas
  pelo usuário/instalação; ambiente de rede confiável; agentes seguem a spec de
  contrato.
- **Restrições duras**: não commitar segredos; nunca `git push` sem pedido; nunca
  `--no-verify`; não enfraquecer defaults de segurança; código runtime só em
  `src/kabbalah/`; um único banco de estado por bridge; auditoria sempre
  append-only; convenção mista PT (docs/domínio) + EN (código/commits) é
  intencional.

---

## 16. Glossário

- **Qlipot**: avaliador de intenção/risco (nome de domínio em PT, mantido).
- **FirewallMCP**: autorizador de ações MCP (RBAC + contratos + score).
- **Contratos / ContratoStore**: verificação de contrato agente-a-agente + estado
  persistido e eventos append-only.
- **HITL**: human-in-the-loop; pendente ≠ aprovado.
- **Cofre**: acesso a segredos (Bitwarden) com cache controlado.
- **LLMGateway / CapabilityRegistry**: seletor canônico de provider por
  role/capability/budget.
- **BudgetLedger / BudgetManager**: ledger append-only + enforcement de limites.
- **HardwareProfiler**: fingerprint e fit/tier de modelos locais por medição.
- **SyncHub**: federação de correções (modelo "definições de antivírus").
- **RiskAssessor**: interface plugável de avaliação de risco (independente do
  fornecedor governado).
- **Kabbalah-Bench**: benchmark de contenção red-team.
- **Trace ID**: `run_id:branch_id:leaf_id`.

---

## 17. Referências

- Arquitetura: `docs/ARCHITECTURE.md`
- Plano de execução (canônico): `docs/roadmap/handoff-execution-plan.md`
- Contexto operacional: `docs/ops/context-pack.md`
- Requisitos EARS (histórico): `docs/specs/requirements.md`
- Política no-mock: `docs/specs/NO_MOCK_RUNTIME_POLICY.md`
- Exit codes CLI: `docs/specs/cli-exit-codes.md`
- Design tree search: `docs/specs/tree-search-design.md`
- Design rede federada: `docs/specs/federated-network-design.md`
- Design group chat ST: `docs/specs/st-group-chat-design.md`
- ADRs: `docs/adr/`
