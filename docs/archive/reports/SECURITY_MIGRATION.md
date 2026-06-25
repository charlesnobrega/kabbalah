# Seguranca - Migracao de Chaves para Cofre

## Status da Migracao

[+] Script de migracao criado: `migrate_keys_to_vault.ps1`
[+] Modulo de leitura segura criado: `src/kabbalah/secrets_vault.py`
[+] Documentacao limpa: `CURRENT_STATUS_REPORT.md`

## Como Migrar

1. Execute o script PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File migrate_keys_to_vault.ps1
   ```

2. O script vai:
   - Ler as chaves do `.env`
   - Mover para `D:\Users\charl\.secrets\keys.json`
   - Limpar o `.env` (deixar apenas placeholders)

## Como Usar no Codigo

```python
from kabbalah.secrets_vault import get_api_key, get_secret

# Obter chave de um provider
openai_key = get_api_key('openai')
google_key = get_api_key('google')
groq_key = get_api_key('groq')

# Obter qualquer segredo
value = get_secret('MY_SECRET_KEY')
```

## Providers Suportados

| Provider      | Chave no Cofre      |
| ------------- | ------------------- |
| OpenAI        | `OPENAI_API_KEY`    |
| Google Gemini | `GOOGLE_API_KEY`    |
| Groq          | `GROQ_API_KEY`      |
| Together      | `TOGETHER_API_KEY`  |
| DeepSeek      | `DEEPSEEK_API_KEY`  |
| Mistral       | `MISTRAL_API_KEY`   |
| Anthropic     | `ANTHROPIC_API_KEY` |
| WAHA          | `waha_api_key`      |

## WAHA Ports

| Conta           | Porta |
| --------------- | ----- |
| Charles Pessoal | 3000  |
| Liliane Esposa  | 3001  |
| Marketing       | 3002  |
| Suporte         | 3003  |
| Sistema         | 3004  |
| Reserva         | 3005  |

## Regras de Seguranca (GEMINI.md)

- [+] NUNCA hardcode credenciais
- [+] NUNCA commite arquivos `.env` com chaves reais
- [+] SEMPRE leia do cofre dinamicamente
- [+] SEMPRE use `secrets_vault.py` para acessar chaves

## Apos Migracao

1. Delete o arquivo `.env` original (opcional, ja foi limpo pelo script)
2. Use apenas `.env.example` como template
3. Atualize providers para usar `secrets_vault.py`
