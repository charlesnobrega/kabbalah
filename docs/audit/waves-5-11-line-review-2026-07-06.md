# Auditoria linha a linha — ondas 5 a 11

Data: 2026-07-06
Branch revisada: `wave-11-federated`
HEAD antes desta auditoria: `9cde944`
Tipo: revisão estática de documentação + código, sem alteração de runtime
Critério: protocolo `ponytail` do handoff — menor relatório útil, achados acionáveis, sem refatoração especulativa

## Veredito curto

As ondas 5, 6, 7, 8, 9 e 11 estão majoritariamente alinhadas ao que o handoff declara. A onda 10 está corretamente bloqueada por decisão humana e não deve ser tratada como pendência de implementação.

Não encontrei evidência estática de vazamento de segredo, execução real dos payloads de benchmark ou bypass crítico imediato. Encontrei gaps úteis para a próxima atualização:

- Budget do `LLMGateway` consulta o `BudgetManager`, mas usa custo projetado `0.0`.
- SyncHub não valida `schema_version` na importação e a proteção contra replay é apenas em memória.
- O handoff promete chave do projeto pré-confiada; o código oferece trust list, mas não embute chave oficial.
- Há drifts documentais pequenos sobre total da suíte e escopo “ondas 4–10” vs “5–11”.
- O texto defensivo contém várias linhas que podem acionar fallback/guardrail em LLMs, especialmente `rm -rf`, base64, exfiltração e shell pipe.

## Escopo revisado

Fonte canônica:

- `docs/ops/context-pack.md:11-13`
- `docs/roadmap/handoff-execution-plan.md:14-35`
- `docs/roadmap/handoff-execution-plan.md:207-288`
- `docs/roadmap/handoff-execution-plan.md:295-304`
- `docs/roadmap/handoff-execution-plan.md:308-315`
- `docs/roadmap/handoff-execution-plan.md:331-466`
- `docs/roadmap/handoff-execution-plan.md:480-520`
- `docs/roadmap/handoff-execution-plan.md:533-568`

Evidências principais:

- `src/kabbalah/llm_gateway.py`
- `src/kabbalah/domain_orchestrator.py`
- `src/kabbalah/budget_manager.py`
- `src/kabbalah/firewall_mcp.py`
- `src/kabbalah/fsm_enforcement.py`
- `src/kabbalah/memory_subsystem.py`
- `src/kabbalah/qlipot.py`
- `src/kabbalah/sync_hub.py`
- `src/kabbalah/configuration_manager.py`
- `src/kabbalah/onboarding.py`
- `src/kabbalah/cli.py`
- `kabbalah_mcp_bridge.py`
- `benchmarks/run.py`
- `benchmarks/scenarios/containment.yaml`
- testes citados no handoff para cada onda

## Matriz linha a linha por onda

| Onda | Linhas do plano | Estado no código | Resultado |
|---|---:|---|---|
| 5.1 Gateway canônico | `217-230` | `LLMGateway` existe e seleciona por role/capability em `src/kabbalah/llm_gateway.py:262-368`. | Implementado, com achado BUD-001. |
| 5.2 OpenAI-compatible | `231-252` | `src/kabbalah/providers/openai_compatible_provider.py` existe; factory/gateway usam provider profiles. | Implementado. |
| 5.3 LeafNode conectado | `253-258` | Sem gateway retorna `status="skipped"` em `src/kabbalah/domain_orchestrator.py:217-234`; com gateway gera artefato real em `267-306`. | Implementado. |
| 5.4 Ledger desde primeira chamada | `259-266` | `BudgetLedger` é append-only; leaf registra custo em `src/kabbalah/domain_orchestrator.py:267-278`. | Implementado. |
| 5.5 HardwareProfiler | `267-285` | `src/kabbalah/hardware_profile.py` existe e é referenciado pelo plano/contexto. | Implementado; sem novo achado nesta leitura. |
| 5.6 Fallback de memória | `287-288` | `memory_subsystem` trata Cognee indisponível como fallback e não exige consistência de backend indisponível em `src/kabbalah/memory_subsystem.py:384-389`. | Implementado. |
| 6.1 RBAC deny-by-default | `297-302` | `FirewallMCP` usa `_deny_all` por padrão em `src/kabbalah/firewall_mcp.py:143-144`; bridge injeta `permitir_tudo` explicitamente em `kabbalah_mcp_bridge.py:162-168`. | Implementado. |
| 6.2 Log no enforcement principal | `303-304` | `check_operation_allowed_with_logging` virou alias depreciado; evidência em `src/kabbalah/fsm_enforcement.py:168-194`. | Implementado. |
| 7.1 BudgetManager | `312` | `BudgetManager` existe com limites run/branch/day/provider em `src/kabbalah/budget_manager.py:124-214`. | Implementado. |
| 7.2 Gateway consulta budget | `313` | Gateway chama `BudgetManager.enforce_call()` em `src/kabbalah/llm_gateway.py:370-377`. | Parcial: ver BUD-001. |
| 7.3 Tool `get_budget_stats` | `314` | Tool exposta em `kabbalah_mcp_bridge.py:1017-1026`. | Implementado. |
| 7.4 Smoke Groq | `316+` | Correções estão refletidas nos testes e no gateway; sem novo achado nesta leitura. | Implementado. |
| 8.-1 Provider matrix | `333-365` | Defaults e tratamentos aparecem em gateway/providers/tests. | Implementado. |
| 8.0 Setup/config | `367-394` | Setup/onboarding e keyring existem; federação usa keyring em `src/kabbalah/configuration_manager.py:454-480`. | Implementado; ver FED-003. |
| 8.1 Model Comparison | `397-401` | Tool `compare_models` em `kabbalah_mcp_bridge.py:1040+`; função em `src/kabbalah/model_comparison.py`. | Implementado. |
| 8.2 Group Chat SillyTavern | `402-406` | `render_group_event` existe em `src/kabbalah/sillytavern_group_chat.py` e no bridge. | Implementado. |
| 8.3 CLI/experiência | `407-421` | CLI principal em `src/kabbalah/cli.py:548`; comandos de config/status presentes. | Implementado. |
| 8.4 Packaging | `422-428` | `pyproject.toml` é fonte canônica; `setup.py` compatível. | Implementado. |
| 8.5 CI | `432-439` | Workflows e testes de metadata existem. | Implementado, não revalidado contra GitHub remoto nesta auditoria. |
| 8.6 Qualidade | `441+` | Baseline do handoff registra ruff e pytest verdes. | Implementado segundo baseline; não reexecutei suíte por ser auditoria documental. |
| 8.7 README-vitrine | `453-466` | README atual descreve produto, quickstart, limites alpha e SillyTavern. | Implementado. |
| 9.1 Kabbalah-Bench | `482-486` | `benchmarks/run.py` e `benchmarks/scenarios/containment.yaml` existem; benchmark declara não executar shell/rede real. | Implementado; ver TRG-002. |
| 9.2 Tree search | `487-488` | `AutonomyLoop` tem modo `tree`, poda por score/budget e fallback linear. | Implementado; ver BUD-002. |
| 10.1 Sandbox real | `494` | Bloqueado no plano; bridge mantém shell desligado por default em `kabbalah_mcp_bridge.py:672-674`. | Bloqueado corretamente. |
| 10.2 RiskAssessor independente | `495-520` | Bloqueado por escolha humana de modelo/infra. Qlipot heurístico segue fallback offline. | Bloqueado corretamente. |
| 11.1 Design federado | `544-546` | `docs/specs/federated-network-design.md` existe. | Implementado. |
| 11.2 Identidade Ed25519 | `547-549` | `ensure_federation_identity()` gera chave e guarda privada no keyring em `src/kabbalah/configuration_manager.py:454-480`. | Implementado. |
| 11.3 Bundles assinados | `550-559` | Export/import assinado em `src/kabbalah/sync_hub.py:150-187`; anonimização testada. | Implementado, com achados FED-001/FED-002/FED-004. |
| 11.4 Trust list/modos | `560-566` | CLI/config oferecem `set-network`, `trust-add`, `trust-remove`. | Parcial: ver FED-003. |
| 11.5 Medição before/after | `567-568` | Resultados datados existem em `benchmarks/results/`; handoff registra 0%→100% no cenário federado. | Implementado. |

## Achados

### BUD-001 — Budget projetado zero no gateway

Severidade: média
Tipo: gap de implementação da onda 7
Linhas: `src/kabbalah/llm_gateway.py:370-377`, `tests/test_llm_gateway.py:436-478`

O gateway chama `BudgetManager.enforce_call()`, mas passa `projected_cost=0.0`. Isso bloqueia quando o gasto anterior já ultrapassou o limite, mas não impede uma chamada que ainda está abaixo do limite e vai ultrapassá-lo. O próprio `BudgetManager` suporta custo projetado real, conforme `tests/test_budget_ledger.py:125-164`.

Recomendação para próxima atualização: usar estimativa simples do profile + tokens esperados, ou aceitar `budget_hint`/`max_tokens` como projeção. Não precisa refatorar o manager.

### BUD-002 — Tree search tem orçamento pré-execução, mas não reserva ledger

Severidade: baixa/média
Tipo: gap de robustez da onda 9
Linhas: `src/kabbalah/autonomy_loop.py:131-145`, `src/kabbalah/autonomy_loop.py:223-236`

O tree search poda ramo acima do budget e chama `BudgetManager.enforce_call()`. Isso é suficiente para bloquear, mas a checagem não reserva custo no ledger. Se o executor real não registrar custo depois, o ledger pode não refletir a decisão de orçamento daquele ramo.

Recomendação para próxima atualização: se `tree` virar modo padrão, adicionar uma reserva append-only ou exigir que todo executor de leaf registre custo.

### FED-001 — Importação de bundle não valida `schema_version`

Severidade: média
Tipo: gap de compatibilidade/segurança da onda 11
Linhas: `src/kabbalah/sync_hub.py:155`, `src/kabbalah/sync_hub.py:165-187`, `docs/specs/federated-network-design.md:43-54`

O bundle exportado inclui `schema_version`, mas `importar_bundle()` não rejeita versão ausente ou incompatível. Ele valida tamanho, replay, trust list, versão do risk assessor e assinatura, mas não a versão do schema.

Recomendação para próxima atualização: rejeitar `schema_version != FEDERATED_BUNDLE_SCHEMA_VERSION` antes de internalizar.

### FED-002 — Replay cache federado é apenas em memória

Severidade: média
Tipo: gap de persistência da onda 11
Linhas: `src/kabbalah/sync_hub.py:84-85`, `src/kabbalah/sync_hub.py:171-186`, `tests/test_sync_hub_federation.py:80-90`

Replay é bloqueado dentro da mesma instância de `SyncHub`, mas `_imported_bundle_signatures` não sobrevive a restart. O teste cobre replay na mesma instância, não replay após reinício.

Recomendação para próxima atualização: persistir assinaturas importadas no SQLite de estado ou em store append-only equivalente. Não precisa sincronização remota.

### FED-003 — Handoff fala em chave do Charles pré-confiada, código só oferece trust list manual

Severidade: baixa/média
Tipo: drift documento/implementação da onda 11
Linhas: `docs/roadmap/handoff-execution-plan.md:560-566`, `src/kabbalah/configuration_manager.py:493-510`, `src/kabbalah/cli.py:315-323`

O plano diz “chave do projeto (Charles) pré-confiada”. O código implementa `trust-add`/`trust-remove`, mas não há chave oficial embutida. Isso é seguro por default, mas não cumpre literalmente a frase do plano.

Recomendação para próxima atualização: só adicionar a chave oficial quando Charles fornecer a public key. Até lá, documentar como “trust list manual”.

### FED-004 — Ordem de validação do bundle difere do design

Severidade: baixa
Tipo: drift de design da onda 11
Linhas: `docs/specs/federated-network-design.md:45-49`, `src/kabbalah/sync_hub.py:171-179`

O design diz verificar assinatura antes de trust list. O código rejeita publicador não confiável antes de validar assinatura. Isso não abre execução nem internalização, mas muda a semântica de auditoria: um bundle adulterado de publicador não confiável vira “untrusted_publisher”, não “signature”.

Recomendação para próxima atualização: escolher uma ordem e alinhar doc/teste. Para economizar CPU, a ordem atual é defensável; para auditoria forense, verificar assinatura primeiro é mais informativo.

### FED-005 — Quórum independente ainda é simplificado para `count >= 3`

Severidade: baixa/média
Tipo: simplificação explícita da onda 11
Linhas: `docs/specs/federated-network-design.md:51-52`, `src/kabbalah/sync_hub.py:269-270`

O design aceita “contagem mínima” ou três publicadores independentes. O código internaliza quando `count >= MIN_FEDERATED_COUNT`. Isso presume que o publicador confiável agregou corretamente os sinais.

Recomendação para próxima atualização: manter como fase 2 se a rede continuar só com bundles curados; exigir publicadores independentes quando houver federação aberta.

### DOC-001 — Total da suíte está inconsistente no handoff

Severidade: baixa
Tipo: drift documental
Linhas: `docs/roadmap/handoff-execution-plan.md:32`, `docs/roadmap/handoff-execution-plan.md:35`

Linha 32 menciona “suíte 1210 verde”; linha 35 registra `1229 passed, 89 skipped`. O baseline mais recente é 1229.

Recomendação: ajustar linha 32 para “suíte verde” ou para o número atual.

### DOC-002 — Context pack ainda fala ondas 4–10

Severidade: baixa
Tipo: drift documental
Linhas: `docs/ops/context-pack.md:11-13`

O context pack diz que o handoff cobre ondas 4–10, mas o handoff atual cobre ondas 4–11 e esta auditoria cobre 5–11.

Recomendação: atualizar a frase para evitar que outra IA ignore a onda 11.

## Superfície de trigger/guardrail

Estes trechos são legítimos para um kernel defensivo, mas têm alta chance de acionar guardrail/fallback em LLMs que analisam conteúdo de segurança:

| ID | Linha(s) | Motivo |
|---|---:|---|
| TRG-001 | `docs/roadmap/handoff-execution-plan.md:14-32` | O próprio protocolo cita fallback Fable→Opus, guardrail e revisão de segurança. Pode sensibilizar a sessão, mas é necessário. |
| TRG-002 | `docs/roadmap/handoff-execution-plan.md:482-484` | Descreve cenários red-team com `rm -rf`, exfiltração via base64, escalada e tool chaining. |
| TRG-003 | `docs/roadmap/handoff-execution-plan.md:508-512` | Explica que o avaliador deve ler conteúdo com cara de ataque sem recusar. Pode ser mal lido como pedido de modelo sem restrição. |
| TRG-004 | `benchmarks/scenarios/containment.yaml:7-9` | Payload declarativo de remoção destrutiva. |
| TRG-005 | `benchmarks/scenarios/containment.yaml:11-19` | Payload base64 envolvendo tokens de produção. |
| TRG-006 | `benchmarks/scenarios/containment.yaml:21-28` | Cadeia `curl ... | sh`. |
| TRG-007 | `benchmarks/scenarios/containment.yaml:30-45` | Destruição em português e homoglyphs. |
| TRG-008 | `src/kabbalah/qlipot.py:71-79`, `src/kabbalah/qlipot.py:422-468` | Regex e decodificação de padrões perigosos. Defesa real, mas textual e semanticamente sensível. |

Observação: `benchmarks/run.py:3-6` declara que o harness mede só o pipeline pré-execução e não invoca shell, rede ou provider live; `benchmarks/run.py:201-216` restringe o `MockProvider` ao trecho de benchmark permitido. Portanto, os payloads acima são dados de teste, não execução.

## Itens que não devem ser “consertados” agora

- Onda 10: continua bloqueada por escolha humana de sandbox/modelo independente.
- `execute_command` com `shell=True`: está atrás de `KABBALAH_BRIDGE_ENABLE_SHELL=1` em `kabbalah_mcp_bridge.py:672-674`; não é regressão das ondas 5–11.
- Trust list manual: é mais seguro do que pré-confiar chave inexistente. Só virar automática quando houver public key oficial.
- Conteúdo ofensivo nos benchmarks: remover isso enfraquece o Kabbalah-Bench. O correto é isolar, comentar e garantir que nunca execute.

## Próxima atualização recomendada

Ordem mínima:

1. Corrigir `schema_version` no SyncHub e adicionar teste.
2. Persistir replay cache federado.
3. Ajustar projeção de custo no `LLMGateway`.
4. Atualizar os dois drifts documentais.
5. Quando Charles fornecer a public key oficial, decidir se entra como trust padrão ou instrução manual no setup.
