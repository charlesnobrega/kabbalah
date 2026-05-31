# Kabbalah Evolution Checklist

Objetivo: implementar melhorias de forma incremental, permitindo rollback simples e validação por etapa.

## Fase 1 - Foundation Safety

- [ ] Budget Manager
- [ ] Token Budget por run_id
- [ ] Cost Budget por run_id
- [ ] Time Budget por run_id
- [ ] Depth Budget por branch
- [ ] Budget Dashboard
- [ ] Testes unitários
- [ ] Testes de carga

### Critério de rollback
- [ ] Budget pode ser desligado por configuração
- [ ] Compatível com execução atual

---

## Fase 2 - Policy Engine

- [ ] Policy Engine
- [ ] Allow List
- [ ] Review List
- [ ] Block List
- [ ] Integração com Tool Execution Engine
- [ ] Auditoria completa

### Critério de rollback
- [ ] Feature Flag
- [ ] Modo legacy preservado

---

## Fase 3 - Skill Registry

- [ ] SecuritySkillRegistry
- [ ] Importação das 754 skills
- [ ] Classificação de risco
- [ ] Indexação no Cognee
- [ ] Busca semântica
- [ ] Mapeamento MITRE ATT&CK
- [ ] Mapeamento NIST
- [ ] Mapeamento D3FEND

### Critério de rollback
- [ ] Registry desacoplado
- [ ] Pode ser removido sem afetar orquestração

---

## Fase 4 - Memory Evolution

- [ ] Working Memory
- [ ] Episodic Memory
- [ ] Long-Term Memory
- [ ] Knowledge Memory
- [ ] Trust Score
- [ ] TTL
- [ ] Memory Decay
- [ ] Promotion Engine

---

## Fase 5 - Meta Orchestrator

- [ ] MetaOrchestrator
- [ ] Controle de custo
- [ ] Controle de profundidade
- [ ] Controle de ramificações
- [ ] Cancelamento de branches inúteis

---

## Fase 6 - Agent Reputation

- [ ] Reputation Engine
- [ ] Score por agente
- [ ] Histórico de acertos
- [ ] Histórico de falhas
- [ ] Seleção dinâmica de agentes

---

## Fase 7 - Meta Evaluator

- [ ] MetaEvaluator
- [ ] Avaliação automática de runs
- [ ] Avaliação de prompts
- [ ] Avaliação de providers
- [ ] Avaliação de skills
- [ ] Recomendações automáticas

---

## Fase 8 - Graph Runtime

- [ ] Execution Graph Runtime
- [ ] Checkpoints
- [ ] Resume after failure
- [ ] Replay
- [ ] Persistência de estado
- [ ] Execução distribuída

---

## Definition of Done

- [ ] Testes passando
- [ ] Documentação atualizada
- [ ] Auditoria validada
- [ ] Compatibilidade mantida
- [ ] Rollback validado
