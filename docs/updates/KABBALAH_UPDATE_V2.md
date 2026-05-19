# Atualização V2 - Especificação Consolidada e Patch de Código

## 1. Visão Geral
Este documento aglutina as definições do motor de Inteligência (*Gemma 4* / *TurboQuant*), a imposição da trava de segurança (*Anti-Mock*), o resgate da fundamentação original do projeto (*Kiro V5+OpenClaude*) e fornece a execução de código literal (*Patch Code*) para mitigar o colapso estrutural visto na bateria local de testes.

---

## 2. Herança Arquitetural: KIRO V5 + OpenClaude
O arcabouço central herdado das validações anteriores e solidificado na arquitetura:
1. **FSM & Árvore (Core Kiro V5):** A recursão linear sai para a entrada da arquitetura nodular em Intake, Root e Leaf.
2. **Abstração Neutra (OpenClaude DNA):** Extinção do vendor lock-in. A interface conecta provedores locais (Ollama/vLLM) e fechados em uma ponte comum.
3. **Memória Cognee:** Operações fundamentadas num framework vetorial sólido.

---

## 3. Auto-Detecção de Hardware & Gemma 4 (TurboQuant)

O motor utiliza um roteador flexível com Sondagem Dinâmica de Ambiente (`Smart Install`).

### Fluxo Híbrido Condicional
O recurso não é fixado em máquina local (`Rig`). O nó `ProviderManager` detecta a densidade da GPU (via CUDA):
* **Com Hardware Presente:** Instancia o **TurboQuant** para 4-bits. A matriz de roteamento é executada sem custo (Zero-cost base) usando hierarquia residente:
  * Gateway via **Gemma 4 E2B**.
  * Abstração central pelo **Gemma 4 26B MoE**.
  * Ações externas/IoT pelo **Gemma 4 E4B**.
* **Sem Hardware / Host de baixa tensão:** Fallback para endpoints gratuitos / Groq remotos. 

---

## 4. O Sistema "Human-In-The-Loop" e Diretriz Anti-Mock

A arquitetura passa de "protótipo avaliativo" a "motor operacional no mundo físico". Regras inflexíveis de execução:
* **Proibição Constante de Mocks:** Nunca invente dados. Um retorno de *API null* é uma exceção tratada `MissingArtifactException`, não tratada com strings sintéticas. 
* **Autorização (Approval Gate):** Agentes com capacidades estendidas (Open Interpreter) param em dry-run e pausam a máquina de estados. O filesystem só pode ser percutido se o admin enviar "sim/liberado".

---

## 5. Cirurgia de Regressão e Application Patches

Executando a matriz local com Property-based testing (Hypothesis/Pytest), identificamos 165 testes reprovados na fundação do Kiro. Abaixo os fix codes obrigatórios para as Falhas (A a D).

### Falha A: Migração da SDK do Google (Gemini)
* **Status:** Quebra violenta em `google.generativeai` e iterador assíncrono falho no teste `test_multiple_requests`.
* **Patch em `google_gemini_provider.py`:**
```python
from google import genai
import asyncio
import os

class GoogleGeminiProvider:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)

    async def _execute_request_async(self, model: str, contents: list):
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self.client.models.generate_content(model=model, contents=contents))
        return response.text

    async def test_multiple_requests(self, requests: list):
        tasks = [self._execute_request_async("gemini-1.5-flash", req) for req in requests]
        return await asyncio.gather(*tasks)
```

### Falha B: Overflow e Recursividade Incorreta do Trace ID
* **Status:** Sobrecarga catastrófica por limitação de string format em indexação.
* **Patch em `trace_id_tracking.py`:**
```python
import uuid
from pydantic import BaseModel, Field

class TraceContext(BaseModel):
    # Uso de hex truncado estancando a expansão fractal do string path.
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    branch_id: str = Field(default_factory=lambda: f"br_{uuid.uuid4().hex[:8]}")
    leaf_id: str = Field(default="")
```

### Falha C: Contratos e Empty Artifacts (Silence Bypass)
* **Status:** O nó aceitava arrays em branco validando a tarefa como feita.
* **Patch em validação de contrato (ex: `contract_enforcement.py`):**
```python
class LeafVerifierContract:
    def validate_leaf_execution(self, artifacts_returned: list) -> str:
        # Repara status de execução de API sintética
        if not artifacts_returned or len(artifacts_returned) == 0:
            raise ValueError("O processamento retornou VAZIO. Redirecionando para REPAIR_MODE.")
        return "SUCCESS"
```

### Falha D: Mismatches do Timestamp na Validação
* **Status:** Validações rejeitando `.isoformat()` ou divergindo `now()` de `utcnow()`.
* **Patch em `models.py`:**
```python
from datetime import datetime, timezone

def get_strict_utc_now() -> datetime:
    # A base única pra qualquer ingestão de Data na Kabbalah inteira.
    return datetime.now(timezone.utc)
```
