# Kabbalah Hardening — Próximas Ondas

> **Nota (2026-07-04)**: as 3 ondas deste documento estão completas. A
> continuação do projeto (ondas 4–10) está especificada em
> [handoff-execution-plan.md](handoff-execution-plan.md).

Este documento consolida melhorias levantadas após a análise técnica de Qlipot,
FirewallMCP, Contratos e Cofre. A Onda 1 já tratou o bridge MCP e o
`ToolExecutionEngine`; os itens abaixo são próximos passos.

## Correção de leitura da auditoria

O achado sobre uppercase em Qlipot/Firewall precisa ser formulado com precisão:
se o código normaliza com `.lower()`, `EXECUTE_COMMAND` não bypassa por
capitalização. O risco real é a dependência de heurística keyword-based:

- payloads codificados;
- unicode homoglyph;
- sinônimos;
- outro idioma;
- comandos indiretos, como variantes de remoção/destruição não listadas.

## Onda 2 — Contratos persistentes e auditáveis

Status: implementada (branch `hardening/wave-2`).

- [x] Criar `ContratoStore` SQLite (`src/kabbalah/contrato_store.py`).
- [x] Persistir contratos ativos, concluídos, violados, revogados e rejeitados.
- [x] Adicionar índice lógico por `(provedor, acao, status)`.
- [x] Tornar `max_calls` transacional/thread-safe (UPDATE atômico com guarda
      no WHERE; caminho em memória protegido por lock).
- [x] Persistir violações em log append-only (`contrato_eventos`, sem API de
      update/delete).
- [x] Separar ausência de contrato de violação real
      (`VerificationOutcome.NO_CONTRACT` + `registrar_ausencia`; ausência não
      escala HITL nem marca contrato como violado).
- [x] Validar restart: contrato ativo antes do restart continua válido depois
      (`tests/test_contrato_store.py`, `tests/test_bridge_hardening_wave2.py`).

## Onda 3 — Scoring e aprendizado

Status: implementada (branch `hardening/wave-2`).

- [x] Normalizar unicode antes da avaliação de risco (NFKC + remoção de
      zero-width + fold de homoglyphs cirílicos/gregos, `_normalizar_texto`).
- [x] Cobrir comandos perigosos reais além de keywords simples (padrões
      regex: `rm -rf`, `dd if=`, `drop table`, `curl|sh`, fork bomb, etc.).
- [x] Adicionar testes contra encoding/base64/homoglyph/sinônimos
      (`tests/test_qlipot_hardening_wave3.py`; payloads base64 são
      decodificados e re-avaliados).
- [x] Restringir `qlipot.aplicar_correcao()` por origem autorizada
      (`origens_autorizadas`, default `{"sync_hub"}`; origem não autorizada
      levanta `PermissionError` e fica registrada).
- [x] Limitar faixa de delta (clamp ±0.30) e registrar correções em
      auditoria append-only (`correcoes_log`).
- [x] Versionar risk assessor (`RISK_ASSESSOR_VERSION` em toda
      `IntentEvaluation` e em cada correção).

Nota de comportamento: nomes contendo `password`/`senha` agora pontuam no
tier de auditoria (0.50), então `read_env_var` de variáveis como
`BW_PASSWORD` escala para HITL antes do allowlist.

## Cofre

Status: implementado (branch `hardening/wave-2`).

- [x] Documentar explicitamente que cache em RAM é um tradeoff de performance
      (docstring do módulo).
- [x] `BITWARDEN_CLI_PATH` fixa o binário `bw` por caminho absoluto,
      eliminando lookup de PATH.
- [x] Validação opcional de hash do binário via `KABBALAH_BW_SHA256`
      (mismatch aborta antes de executar).
- [x] `clear_on_read=True` para segredos críticos (cache serve uma única
      vez) e `limpar_cache()` explícito.

## Observação estratégica

O posicionamento técnico do Kabbalah continua sendo autorização de ações em
runtime, especialmente sobre MCP. Isso é diferente de guardrails focados apenas
em conteúdo/prompt/output.
