# Kabbalah - Next Generation Roadmap: The Intelligence Engine

Este documento documenta os conceitos avançados de evolução do projeto definidos na fase de planejamento, com foco total no refinamento do **Motor de Inteligência e Decisão** do sistema.

## O Desafio Principal
À medida que agregamos "braços e pernas" ao sistema (atuadores e abstrações), o problema não é mais fazer, é **saber quando (e com qual custo) utilizar cada função**. O motor de decisão precisa ser hiper-inteligente sobre o gerenciamento de recursos.

---

## 0. DIRETRIZ GLOBAL DE EXECUÇÃO (Mandatório)
- **PROIBIÇÃO DE MOCKS:** O sistema está absolutamente **proibido de usar dados mockados** (falsos/simulados). Todas as integrações, chamadas ou execuções devem ocorrer no ambiente real com dados concretos limitados pelas credenciais presentes. Caso os dados não existam, a inferência deve falhar e cobrar o input, nunca inventar ou simular o retorno.
- **AUTORIZAÇÃO HUMANA (Human-in-the-Loop):** Toda e qualquer ação de execução que modifique o filesystem, envie comandos à infraestrutura física, gere código novo ou atue em APIs externas exige validação. O motor deve sempre pausar o fluxo e **solicitar autorização expressa do usuário (humano)**. A atuação só é liberada com consentimento explícito.

---

## 1. Roteamento Inteligente & Custos (Cost-Aware Routing)

### 1.1 Roteador Bayesiano (Zero-Cost Routing)
- **Conceito:** Inspirado no `multi-agent-router` acoplado ao modelo ultraleve **Gemma 4 E2B**.
- **Lógica:** Em vez do *Root Orchestrator* gastar tokens enviando a task inteira para o GPT-4 decidir quem cuida do problema, rodamos o filtro local (Gemma 2B + Jaccard Keywords/Embeddings). 
- **Decisão Instantânea:** Escolha determinística da tribo de agentes em <200ms na GPU, consumindo quase zedo de VRAM.

### 1.2 "Radar" de Modelos Free em Agregadores
- **Conceito:** Um agente daemon paralelo monitora constantemente agregadores multimodelo (ex: OpenRouter, HuggingFace Inference, Together).
- **Lógica:** Subtarefas de processamento trivial (parsear JSON, estruturar log) são desviadas autonomamente pelo motor para chamadas de APIs que no momento estejam 100% gratuitas ou sejam mais baratas. Nós preservamos os modelos High-End (Claude/GPT-4) apenas para a orquestração e código criativo.

---

## 2. Capacidade Executiva Real e Atuadores

### 2.1 Módulo Home Assistant (IoT)
- **Conceito:** Interface MCP (Model Context Protocol) nativa apontada para broker/ponte de API doméstica.
- **Lógica:** O motor sabe distinguir se a tarefa é "software" ou "ambiente físico", acionando as APIs de automação. **(O Leaf Agent designado aqui rodará nativamente na flag `google/gemma-4-4b` devido ao seu excelente suporte a Function Calling).**

### 2.2 Execução Agressiva (Nativamente via Open Interpreter)
- **Conceito:** O sistema recebe permissões estendidas no filesystem e no terminal, orquestrado pelo Gemma 4 para alta previsibilidade local.
- **Lógica:** É expressamente proibido mockar operações de terminal. O sistema criará e engatilhará scripts Python verdadeiros on-the-fly. **REGRA VITAL:** O sistema sempre pausará a queue, demonstrará o comando/script e pedirá autorização do usuário; o script real só é disparado no host *após* liberação do administrador.

---

## 3. Auto-Evolução Sustentável (Human-In-The-Loop)

- **Conceito:** O código passa a ser auto-monitorado (profiling contínuo da Fase 6 - Observabilidade).
- **Lógica:** O sistema detecta gargalos com dados vivos de observabilidade (ex: *"Essa função tem latência de 2s"*). Nenhum payload simulado será admitido para a reprofilagem.
- **Ação Restrita:** A melhoria estrutural entra na memória semântica como um "Alerta de Upgrade". É forçosamente necessário que o usuário (Humano) avalie o plano e digite a autorização. Sem essa aprovação do usuário de forma declarativa, zero mutações ou execuções locais ocorrerão.

---

## 4. Experiência de Uso e Auto-Configuração (Foco em Deploy)

### 4.1 Interface de Interação (Web Dashboard)
- **Conceito:** Uma API superleve (FastAPI) expõe o motor do Kabbalah.
- **Lógica:** O usuário acompanha visualmente (via página web no PC ou Celular) a árvore de decisão do sistema, os logs de auditoria e pode despachar tarefas ("Desligue tudo", "Faça a análise financeira") conversando com a máquina sem lidar com o terminal.

### 4.2 Auto-Detecção de Hardware no Setup (Smart Install)
- **Conceito:** O script de instalação `setup.py` checa o cenário físico local.
- **Lógica:** Se a rig de instalação possuir aceleração (GPUs / CUDA detectadas nativamente), o sistema liga automaticamente a diretriz do **OLLAMA / Modelo Local** na árvore do `Hierarchy Provider Mode`. O sistema passa a injetar chamadas 100% gratuitas nas tarefas leves e reserva os provedores na nuvem apenas para as sub-tarefas de alto custo mental.
