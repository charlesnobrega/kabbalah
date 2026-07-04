# Projeto Kabbalah: Implementação do TurboQuant (KV Cache Compression)

## O Contexto da Pesquisa (Paper arXiv:2504.19874)
O TurboQuant, revelado pelo artigo "*TurboQuant: Vector Quantization for KV Cache Compression*" (Google DeepMind, 2026), alcança o que era considerado impossível: comprimir o contexto (memória de curto prazo da IA) em **3 a 4 bits**. Ele faz isso aplicando rotação ortogonal aleatória e quantização escalar de Lloyd-Max. 

Para a nossa **Rig de 3x GTX 1660 (18GB total)**, isso significa que podemos entupir o "contexto" da LLM com páginas da documentação do Home Assistant, código de programação e a transcrição da reunião, e a VRAM da placa não vai acabar.

## Como Implementar isso no Kabbalah

Em vez de escrevermos a matemática pesada (Tensores do PyTorch) do zero no código do Kabbalah, a comunidade Open-Source já criou a ponte perfeita. 

### Arquitetura de Integração

1. **O Motor Local (vLLM)**
   - Abandonamos o `Ollama` padrão para inferência avançada local e adotamos o **vLLM** (que roda na máquina host do Linux).
   - *Por quê:* O vLLM é focado em alta performance (serve o modelo muito mais rápido nas GPUs e lida com requests paralelos).

2. **O Plugin (`turboquant-vllm`)**
   - Não precisamos alterar o código-fonte do vLLM. Já existe um pacote pip comunitário chamado `turboquant-vllm`.
   - **Comando de Instalação no Linux Host:** 
     `pip install vllm turboquant-vllm`

3. **Iniciando o Servidor na Mining Rig**
   - Você roda o modelo na shell da sua máquina chamando o plugin para esmagar o cache na memória das 3 GPUs:
     ```bash
     # Passo 0: Verificar compatibilidade da arquitetura (Obrigatório)
     python -m turboquant_vllm.verify --model google/gemma-4-26b-moe --bits 4

     # Passo 1: Iniciar o servidor
     python -m vllm.entrypoints.openai.api_server \
       --model google/gemma-4-26b-moe \
       --kv-cache-dtype turboquant_4bit \
       --tensor-parallel-size 3 # Distribui nas suas 3 placas 1660
     ```

4. **A Ponte no Código do Kabbalah**
   - No `src/kabbalah/providers/`, nós configuramos o proveder para apontar para a máquina local usando o "format" da API da OpenAI.
   - **Arquivo `.env` final:**
     ```env
     KABBALAH_PROVIDER_MODE=hybrid
     KABBALAH_LOCAL_PROVIDER=openai
     KABBALAH_LOCAL_BASE_URL=http://localhost:8000/v1
     KABBALAH_LOCAL_MODEL=google/gemma-4-26b-moe
     ```

### Conclusão Técnica
O Root Orchestrator do Kabbalah (o cérebro) sequer precisa saber o que é TurboQuant. Ele simplesmente fará uma requisição REST (api) para um modelo super inteligente achando que está chamando a Nuvem, mas na verdade a requisição vai bater na sua própria placa de vídeo na sala, que foi "hackeada" pelo pacote `turboquant-vllm` para conter toda essa memória gigante sem estourar.
