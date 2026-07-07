# Hybrid Risk-Judge — Design (Wave 13.4c)

> **Status**: design para aprovação do Charles (sem código ainda). Segue o padrão
> "design doc primeiro" do repo (cf. `tree-search-design.md`,
> `federated-network-design.md`).
> **Origem**: Wave 13.4b provou com números que um juiz de risco LLM independente
> supera a heurística em falso-positivo com contenção igual — mas a ~100× de
> latência + custo + dependência de nuvem. Este doc especifica como capturar o
> ganho sem pagar o custo no caminho comum.

## 1. Problema

- **Heurística** (`HeuristicRiskAssessor`): ~19ms, offline, determinística. Mas é
  keyword/regex — **super-bloqueia** pedidos benignos que só *mencionam* strings
  perigosas (13.4b: 100% de falso-positivo no conjunto `scenarios_hard`).
- **Juiz LLM** (`LLMRiskAssessor`): entende intenção → falso-positivo 100%→25% com
  a mesma contenção de ataque. Mas ~1956ms, custo por chamada e dependência de
  provider externo.

Rodar o LLM em **toda** ação é caro e frágil. Rodar só a heurística deixa
falso-positivo alto, o que empurra o operador a afrouxar/desligar o kernel — pior
para a segurança no fim.

## 2. Objetivo

Um avaliador **híbrido** que use a heurística barata como primeiro passo e escale
para o juiz LLM **apenas na minoria arriscada**, reduzindo falso-positivo sem
pagar latência no caminho benigno comum, mantendo o kernel **fail-closed**.

Não-objetivos: substituir a heurística; criar provider novo; chamadas LLM
ilimitadas; enfraquecer qualquer default de segurança.

## 3. Desenho

### 3.1 Fluxo
```
avaliar_intencao(pedido, ferramenta, argumentos)
  → h = heuristica.assess_risk(...)                 # sempre, ~19ms
  → se h < T_ESCALA:            return h            # caminho benigno rápido (sem LLM)
  → senão (h alto → bloquearia): 
        j = juiz_llm.assess_risk(...)  (temperature=0)
        se juiz indisponível/erro:     return h     # FAIL-CLOSED: mantém o bloqueio
        return combinar(h, j)                        # ver 3.3
```

A intuição: o modo de falha da heurística observado no 13.4b é **falso-positivo**
(bloquear benigno). Então só escalamos quando a heurística **já bloquearia**
(`h ≥ T_ESCALA`), para o juiz **confirmar ou rebaixar**. Ações claramente benignas
(`h < T_ESCALA`) nunca pagam a chamada LLM.

### 3.2 Fail-closed (regra dura)
- Juiz LLM indisponível, erro de rede/parse, ou timeout → **mantém a decisão da
  heurística** (nunca "abre" por falha do juiz). Isto preserva a contenção mesmo
  offline. (O `LLMRiskAssessor` já faz fallback para a heurística; aqui o híbrido
  garante que o fallback nunca rebaixa um bloqueio.)
- O juiz só pode **rebaixar** um bloqueio da heurística se responder com sucesso e
  score baixo. Nunca pode elevar risco a ponto de contornar o pipeline — o
  Firewall/HITL/contratos seguem por cima, inalterados.

### 3.3 Combinação de scores (proposta, validar no bench)
- `h ≥ T_ESCALA` e `j` baixo (`j < T_BENIGNO`, ex. 0.30) → **rebaixa**: retorna `j`
  (o benigno passa). Este é o ganho principal (mata o falso-positivo).
- `h ≥ T_ESCALA` e `j` alto → **mantém alto**: retorna `max(h, j)` (ataque real
  segue bloqueado).
- Zona cinza (`T_BENIGNO ≤ j < T_ESCALA`) → **rota para HITL** em vez de allow/deny
  automático (humano confirma). Fail-safe: pendente ≠ aprovado (já é o padrão).

### 3.4 Configuração (opt-in — default não muda)
- `KABBALAH_RISK_JUDGE_MODE = heuristic | llm | hybrid` — **default `heuristic`**
  (comportamento atual inalterado; nenhum custo/dependência nova sem opt-in).
- `KABBALAH_RISK_JUDGE_ROLE` — role para selecionar o perfil `risk-judge` no
  gateway (default `Root_Orchestrator`; hoje resolve para OpenRouter).
- `KABBALAH_RISK_ESCALATE_THRESHOLD` (T_ESCALA, default ~0.60) e
  `KABBALAH_RISK_BENIGN_THRESHOLD` (T_BENIGNO, default ~0.30).
- Opção custo-zero/privacidade: apontar o role para um perfil **local (Ollama)** —
  juiz sem custo e sem dados saindo da máquina.

### 3.5 Auditoria
Cada decisão híbrida registra: `h`, `j` (se escalou), qual venceu, identidade do
juiz (`llm-<perfil>:<model>` ou `fallback-...`) e `RISK_ASSESSOR_VERSION` — no
mesmo padrão append-only da onda 3/10.2. Escalou ou não escalou também é auditável
(para medir taxa de escalada em produção).

## 4. Pontos de integração (código, quando aprovado)
- Novo `HybridRiskAssessor(heuristic, llm, t_escala, t_benigno)` implementando o
  protocolo `QlipotRiskAssessor` — **reuso**, não reescrita: compõe os dois
  assessors que já existem (`risk_assessor.py`).
- `Qlipot` já aceita `risk_assessor` injetado — o bridge/CLI escolhe o assessor
  conforme `KABBALAH_RISK_JUDGE_MODE`. Nenhuma mudança no Firewall/HITL/contratos.
- Ollama como juiz local: já suportado pelo registry (`ollama-local-default` tem
  capability `risk-judge`); só precisa do endpoint ativo.

## 5. Como medir (gate de aceite)
Rodar o Kabbalah-Bench nos três modos sobre `benchmarks/scenarios_hard` (e um
conjunto benigno de produção maior, a criar):
- **Contenção de ataque**: híbrido = heurística = 100% (não pode regredir).
- **Falso-positivo**: híbrido << heurística (meta: aproximar do juiz puro, ~25%
  ou menos), idealmente 0% se a zona-HITL absorver os limítrofes.
- **Overhead de latência**: ~0 no caminho benigno (`h < T_ESCALA` não chama LLM);
  custo LLM só na fração escalada. Medir a **taxa de escalada**.
- **Fail-closed**: com o juiz forçado a indisponível, contenção permanece 100%.

## 6. Critérios de aceite (espelha handoff §3 Onda 13.4c)
- [ ] `HybridRiskAssessor` compondo heurística + juiz, com os 3 modos por env.
- [ ] Fail-closed provado por teste (juiz indisponível → decisão da heurística).
- [ ] Bench mostra FP menor que a heurística pura, contenção 100%, overhead de
      latência só nos casos escalados.
- [ ] Default de segurança inalterado quando `MODE=heuristic` (sem regressão na
      suíte; sem chamada de rede no caminho default).
- [ ] Auditoria registra h, j, vencedor, identidade do juiz e taxa de escalada.

## 7. Riscos
- **Juiz rebaixa um ataque real** (falso-negativo do LLM): mitigado por escalar só
  a partir de bloqueio da heurística + zona-HITL + `max(h,j)` no caso alto; e o
  bench mede contenção antes de promover qualquer default.
- **Custo/latência sob ataque em rajada** (muitas ações arriscadas → muitas
  chamadas LLM): limitar via cache de decisão por `assinatura_acao` (já existe no
  Qlipot) e/ou teto de escaladas por run (integra BudgetManager).
- **Dependência de nuvem**: preferir juiz local (Ollama) onde independência e
  custo zero importam mais que latência.
