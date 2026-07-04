# Kabbalah — Plano de Limpeza e Refatoração (Handoff)

> **Gerado por**: Claude Fable 5, 2026-07-04, após inventário completo do repositório
> (tracked files, código órfão, duplicatas e estrutura de docs — todos os alvos abaixo
> foram **verificados por comando**, não presumidos).
> **Executor alvo**: IA de codificação, sob direção de Charles Nóbrega.
> **Objetivo**: repositório limpo, honesto e navegável, pronto para publicar no GitHub.
> **Este plano é a versão detalhada e definitiva da Onda 4 do
> [handoff-execution-plan.md](handoff-execution-plan.md)** — execute este no lugar dela.
> Regras gerais do executor (§2 do handoff) valem aqui: um commit por fase, suíte de
> testes antes/depois, nunca `--no-verify`, nunca push sem pedido do Charles.

## Estado verificado (2026-07-04)

- Tracked: 109 `docs/` · 69 `tests/` · 53 `src/` · 6 `archive/` · ~30 relatórios na raiz
  · 3 `kabbalah/` (raiz) · 1 `phase_4/` · 3 `scripts/` · 1 `config/` · 3 `.github/`.
- `.env`, `.kabbalah_bridge_state.sqlite3` e `.hypothesis/` estão **corretamente
  gitignorados e não tracked** (verificado com `git check-ignore` + `git ls-files`).
- Untracked no disco (não vão ao GitHub, mas sujam o repo local): `openclaude/`
  (clone Git de projeto TypeScript alheio), `workspace/` (milhares de arquivos:
  cópias antigas do pacote, specs `.kiro`, relatórios), `.kiro/`, `.pytest_cache/`,
  `__pycache__/`, `pytest.log`.
- Baseline de testes: `1127 passed, 89 skipped` (skips = providers live, esperado).
  **Atenção**: a Fase B remove um arquivo de teste duplicado — o novo baseline de
  `passed` será menor. Registre o número novo neste arquivo ao concluir.

---

## FASE A — Segurança pré-GitHub (OBRIGATÓRIA, primeiro)

O repo teve incidente de chave no passado (evidência: `SECURITY_ALERT.md`,
`SECURITY_MIGRATION.md`, `scripts/migrate_keys_to_vault.ps1`). Antes de qualquer
push público:

- [x] **A.1** Rodar um scanner de segredos no **histórico completo**, não só no
  working tree: `gitleaks detect --source . --log-opts="--all"` (ou trufflehog).
  - Se encontrar segredo em commit antigo: **PARE e reporte ao Charles** com a lista
    de commits/arquivos. A decisão entre reescrever histórico (BFG/filter-repo) ou
    publicar como repo novo órfão é dele (gate #5 do handoff, adicionado abaixo).
  - Se limpo: registre o resultado aqui e siga.
  - Resultado Codex 2026-07-04: `gitleaks detect --source . --log-opts="--all" --redact=100`
    executado com relatório temporário fora do repo; `0` achados.
- [ ] **A.2** Confirmar de novo, pós-limpeza (final da Fase F): `git ls-files | grep
  -iE "\.env$|sqlite|secret|credential|apikey"` → vazio (exceto código/docs).

---

## FASE B — Remover duplicatas e código morto (tracked)

Cada alvo abaixo foi verificado hoje. Antes de cada remoção, rode a verificação
indicada; se ela divergir, investigue antes de remover.

- [x] **B.1** `kabbalah/` (diretório na RAIZ — não confundir com `src/kabbalah/`):
  3 arquivos tracked, duplicata de `archive/legacy/kabbalah-root-package/`.
  Verificar: `diff -r kabbalah/ archive/legacy/kabbalah-root-package/` (esperado:
  idêntico ou trivial). Então `git rm -r kabbalah/`.
- [x] **B.2** `phase_4/` (raiz): 1 arquivo, duplicata de `archive/legacy/phase_4/`.
  Mesmo procedimento. `git rm -r phase_4/`.
- [x] **B.3** `tests/test_error_analysis_module_backup.py`: arquivo "backup" que roda
  na suíte duplicando testes; cópia já existe em `archive/legacy/tests/`.
  `git rm tests/test_error_analysis_module_backup.py`. Registrar o novo total de
  `passed` no baseline.
  - Resultado Codex 2026-07-04 após B.1–B.4: suíte completa permaneceu em
    `1127 passed, 89 skipped`.
- [x] **B.4** Módulos órfãos em `src/kabbalah/` (zero referências em `src/`, `tests/`,
  bridge e `setup.py` — verificado por varredura de identificadores):
  - `src/kabbalah/error_detection.py` (o módulo usado é `error_detection_module.py`)
  - `src/kabbalah/self_healing.py` (o usado é `self_healing_models.py`)
  Verificar antes: `grep -rn "error_detection\b" src tests kabbalah_mcp_bridge.py`
  (cuidado com o falso-match do sufixo `_module`; confira cada hit) e o equivalente
  para `self_healing\b`. Confirmado órfão → `git rm` (o histórico git preserva;
  não criar cópia em archive).
- [x] **B.5** Imports e variáveis não usados no código vivo: adicionar `ruff` a
  `requirements-dev.txt`, criar `ruff.toml` mínimo (`select = ["F401", "F841"]`,
  `target-version = "py39"`), rodar `ruff check src tests kabbalah_mcp_bridge.py
  --fix`, revisar o diff manualmente (não aceitar remoção cega em `__init__.py`
  de pacote — ali import "não usado" pode ser API pública; use `__all__` como guia).
  Commit separado.
  - Resultado Codex 2026-07-04: `ruff check src tests kabbalah_mcp_bridge.py`
    limpo; suíte completa `1127 passed, 89 skipped`.

---

## FASE C — Lixo local untracked ("não deixar nada para trás")

Não afeta o GitHub, mas o pedido é repo limpo por completo. **Regra: mover para fora
do repo antes de apagar** — deletar só o que for confirmadamente descartável.

- [x] **C.1** `openclaude/`: clone de projeto TS alheio, zero imports (verificado).
  Deletar do disco. (Se o Charles quiser guardar, mover para `E:\projetos\openclaude`
  — já existe um diretório com esse nome lá; nesse caso apenas delete o daqui.)
- [x] **C.2** `workspace/`: área de desenvolvimento antiga com cópias desatualizadas
  do pacote e specs. Antes de apagar: conferir se `workspace/.kiro/specs/kabbalah/`
  (requirements.md, design.md) tem conteúdo que NÃO existe em `docs/specs/` — se
  tiver algo único e valioso, copiar para `docs/archive/kiro-specs/`. Depois mover
  `workspace/` inteiro para `E:\projetos\_kabbalah_workspace_backup\` (fora do repo).
  Após confirmação do Charles, ele apaga o backup quando quiser.
- [x] **C.3** Apagar do disco: `.pytest_cache/`, `__pycache__/` (todos), `pytest.log`.
  Conferir `.gitignore` cobre: `pytest.log`, `.pytest_cache/`, `__pycache__/`,
  `*.sqlite3`, `.hypothesis/` — adicionar o que faltar.
- [x] **C.4** `.kiro/` (raiz): specs de ferramenta antiga. Mesmo tratamento do C.2
  (conferir conteúdo único → arquivar → remover do disco).
  - Resultado Codex 2026-07-04: specs únicas arquivadas em
    `docs/archive/kiro-specs/`; `workspace/` movido para
    `E:\projetos\_kabbalah_workspace_backup\workspace`; `openclaude/`, `.kiro/`,
    `.pytest_cache/`, `__pycache__/` e `pytest.log` removidos. Scan redigido do
    arquivo Kiro: `0` achados.

---

## FASE D — UM único documento de arquitetura + consolidação de docs

Pedido explícito do Charles: **deve existir um único documento de arquitetura** e o
repo não pode ter "arquivo solto sem sentido". Estado atual de `docs/`: 109 arquivos,
sendo 40 já em archive, 29 em specs (maioria morta), 17 em audit, 6 updates, etc.

- [ ] **D.1** Criar **`docs/ARCHITECTURE.md`** — o documento único — consolidando:
  1. `docs/architecture/CURRENT_ARCHITECTURE.md` (estado atual),
  2. `docs/architecture/REPOSITORY_STRUCTURE.md` (estrutura alvo),
  3. `docs/PROJECT_STRUCTURE.md`,
  4. o diagrama e as decisões canônicas do §1 do `handoff-execution-plan.md`
     (referenciar, não duplicar — o handoff continua sendo o plano de execução).
  Estrutura sugerida: Visão geral → Camadas (diagrama) → Componentes e
  responsabilidades → Decisões canônicas → Persistência → Estrutura de diretórios →
  Referências (ADRs, roadmap). Depois: `git rm` dos 3 arquivos absorvidos.
  Os 6 ADRs em `docs/adr/` PERMANECEM (são registros de decisão datados, padrão
  correto) — o ARCHITECTURE.md aponta para eles.
- [ ] **D.2** Mover `MELHORIAS_E_APRIMORAMENTOS.md` da raiz para
  `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md` e **atualizá-lo**: marcar nos itens
  M13–M16 o que esta limpeza concluir (✅ + data), corrigir o M15 (o README atual já
  é honesto — o que restava era arquivar relatórios, feito na Fase E) e adicionar no
  topo um bloco "Status vivo: ver docs/roadmap/handoff-execution-plan.md §0".
- [ ] **D.3** Triagem de `docs/specs/` (29 arquivos). MANTER apenas os vivos:
  `NO_MOCK_RUNTIME_POLICY.md`, `CONFIGURATION_GUIDE.md`,
  `PROVIDERS_IMPLEMENTATION_GUIDE.md`, `PROVIDER_HIERARCHY.md`,
  `PROVIDER_SETUP_LINKS.md`, `PROVIDER_TESTING_STRATEGY.md`, `API_KEY_SECURITY.md`,
  `REPOSITORY_AUDIT.md`, e `requirements.md`/`design.md`/`tasks.md` (specs do kernel).
  ARQUIVAR em `docs/archive/specs/`: todos os `PHASE4_*` (7), `EXECUTIVE_SUMMARY.md`,
  `VALIDATION_REPORT.md`, `PROJECT_RECOVERY_REPORT.md`, `AUDIT_REPORT.md`,
  `INTEGRATED_ROADMAP.md`, `NEXT_GEN_ROADMAP.md` (conflitam com o roadmap oficial),
  `MEMORY_ANALYSIS.md`, `EVOLUTION_CHECKLIST.md`, `SECURITY_SKILL_REGISTRY_ANALYSIS.md`,
  `TURBOQUANT_IMPLEMENTATION.md`. Remover `docs/specs/.config.kiro`.
- [ ] **D.4** `docs/updates/` (6) e `docs/superpowers/` (1): ler por alto; se
  descrevem estado passado → `docs/archive/`; se vivos, integrar ao doc certo.
- [ ] **D.5** Raiz → `docs/archive/reports/`: `git mv` de TODOS os relatórios de
  status/fase da raiz (~30: `PHASE*_*.md`, `FINAL_*.{md,txt}`, `PROJECT_*.md`,
  `SESSION_*.md`, `TASK_*_SUMMARY.md`, `CURRENT_STATUS_REPORT.md`,
  `KABBALAH_PROJECT_STATUS.md`, `QUICK_REFERENCE.md`, `PROVIDER_*.md`,
  `PHASES_7_8_COMPLETION_REPORT.md`, `findings.md`, `progress.md`, `task_plan.md`).
  Destinos especiais: `CREATE_REPO_GITHUB.md` → `docs/development/`;
  `SECURITY_ALERT.md` + `SECURITY_MIGRATION.md` → `docs/security/` se a migração de
  chaves ainda for referência viva, senão archive.
  **Raiz final permitida** (≤ 14 itens): `README.md`, `LICENSE`, `CONTRIBUTING.md`,
  `setup.py`, `pytest.ini`, `ruff.toml`, `requirements*.txt` (5),
  `kabbalah_mcp_bridge.py`, `sillytavern_config.json`, `sillytavern_mcp_config.json`,
  `.gitignore`, `.gitattributes`, `.env.example`.
- [ ] **D.6** Atualizar `README.md`: seção "Repository layout" reflete a árvore nova;
  "Important docs" aponta para `docs/ARCHITECTURE.md` + roadmap + governança;
  remover links quebrados (validar todos os links relativos do README).

---

## FASE E — Higiene de git

- [ ] **E.1** Criar `.gitattributes` com `* text=auto` (elimina os warnings CRLF/LF
  constantes no Windows). Em commit separado: `git add --renormalize .` — o diff
  será grande porém só de line endings; não misturar com nenhuma outra mudança.
- [ ] **E.2** Revisar `.github/` (3 arquivos): workflows/templates apontam para
  caminhos que a limpeza moveu? Corrigir.
- [ ] **E.3** `scripts/PUSH_TO_GITHUB.sh`: ler; se contiver URL de remoto pessoal ou
  passos obsoletos, atualizar ou remover (o push é decisão manual do Charles).

---

## FASE F — Verificação final e definição de pronto

- [ ] **F.1** Suíte completa: 0 failed; registrar novo baseline aqui: `____ passed,
  89 skipped`.
- [ ] **F.2** `pip install -e .` limpo + `python -m kabbalah.cli --help` exit 0.
- [ ] **F.3** Raiz com ≤ 14 arquivos (lista da D.5); `git ls-files | wc -l` reduzido
  (~230, era ~280); nenhum diretório untracked sobrando além de `.venv/`.
- [ ] **F.4** Re-rodar A.2 (grep de sensíveis) e A.1 se o histórico foi reescrito.
- [ ] **F.5** README revisado por leitura completa — é a cara do repo no GitHub.
- [ ] **F.6** Atualizar este arquivo (checkboxes + baselines) e o §0 do
  `handoff-execution-plan.md` (marcar Onda 4 como concluída via este plano).

## O que NÃO fazer

- Não tocar em `src/kabbalah/` além do B.4/B.5 — refatoração de arquitetura é das
  ondas 5+ do handoff, não da limpeza.
- Não apagar `archive/legacy/` nem `docs/archive/` — arquivar ≠ deletar; histórico
  falso vira histórico *arquivado e rotulado*, não buraco de memória.
- Não apagar `docs/audit/` (17 arquivos): são os laudos forenses que documentam a
  linhagem do projeto — mantê-los é parte da honestidade do repo.
- Não mexer em `.env` real, `.venv/`, banco sqlite de estado.
- Não fazer o push ao GitHub — preparar é o escopo; publicar é do Charles.

## Gate adicional para o Charles

| # | Decisão | Bloqueia |
|---|---|---|
| 5 | Se A.1 achar segredo no histórico: reescrever histórico (BFG) ou publicar repo novo órfão? | Push ao GitHub |
