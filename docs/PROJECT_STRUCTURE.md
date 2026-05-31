# Project Structure

Este documento define uma organização prática para o projeto Kabbalah.

## Objetivo

Manter o projeto fácil de entender, codificar, auditar e reverter quando uma mudança der problema.

## Estrutura recomendada

```text
kabbalah/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── adr/
│   ├── architecture/
│   ├── development/
│   ├── governance/
│   └── specs/
├── src/
│   └── kabbalah/
│       ├── agents/
│       ├── orchestration/
│       ├── runtime/
│       ├── memory/
│       ├── providers/
│       ├── tools/
│       ├── security/
│       ├── observability/
│       └── config/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── examples/
└── scripts/
```

## Responsabilidade por diretório

| Diretório | Função |
|---|---|
| `docs/specs` | requisitos, design e tarefas do projeto |
| `docs/adr` | decisões arquiteturais importantes |
| `docs/architecture` | visão técnica e diagramas |
| `docs/development` | fluxo de trabalho, branches e rollback |
| `docs/governance` | políticas de execução, segurança e revisão |
| `src/kabbalah/agents` | Intake, Root, Domain, Leaf, Verifier, Auditor, Synthesizer |
| `src/kabbalah/orchestration` | árvore de execução e coordenação |
| `src/kabbalah/runtime` | FSM, modos BOOTSTRAP/DAY1/DAY2, checkpoints |
| `src/kabbalah/memory` | Cognee, JSONL fallback, memória hierárquica |
| `src/kabbalah/providers` | abstração de LLMs e fallback |
| `src/kabbalah/tools` | Tool Execution Engine e sandbox |
| `src/kabbalah/security` | Policy Engine, Skill Registry e Execution Guard |
| `src/kabbalah/observability` | logs, métricas, trace_id e auditoria |
| `src/kabbalah/config` | configuração central do runtime |

## Regra de ouro

Nenhuma funcionalidade grande deve ser implementada direto na `main`.

Use branches pequenas:

```text
feature/budget-manager
feature/policy-engine
feature/skill-registry
feature/memory-evolution
feature/meta-orchestrator
```

## Critério para merge

Uma branch só deve ser mesclada quando:

- [ ] testes passam;
- [ ] documentação foi atualizada;
- [ ] rollback foi considerado;
- [ ] logs/auditoria foram preservados;
- [ ] não quebrou compatibilidade com o fluxo atual.
