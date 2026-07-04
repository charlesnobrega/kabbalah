# Kabbalah Hardening — Próximas Ondas

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

- Normalizar unicode antes da avaliação de risco.
- Cobrir comandos perigosos reais além de keywords simples.
- Adicionar testes contra encoding/base64/homoglyph/sinônimos.
- Restringir `qlipot.aplicar_correcao()` por origem autorizada/capability.
- Limitar faixa de delta e registrar correções em auditoria.
- Versionar risk assessor para rastrear decisões históricas.

## Cofre

- Documentar explicitamente que cache em RAM é um tradeoff de performance.
- Avaliar `BITWARDEN_CLI_PATH` fixo para reduzir risco de PATH injection.
- Avaliar validação opcional de hash/assinatura do binário `bw`.
- Considerar TTL menor ou clear-on-read para segredos críticos.

## Observação estratégica

O posicionamento técnico do Kabbalah continua sendo autorização de ações em
runtime, especialmente sobre MCP. Isso é diferente de guardrails focados apenas
em conteúdo/prompt/output.
