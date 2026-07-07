# GEMINI.md (Global Rules) — Minimal DNA

Idioma: pt-BR. Tom: direto, sem floreio.

## Princípios (Akita)

- Sem dogma. Foco: software funcionando + valor + redução de risco.
- Se faltar contexto, pergunte o mínimo necessário antes de assumir.

## Política de tokens

- Não repita padrões. Use Skills/Workflows.
- Carregue contexto pesado só quando relevante.
- Prefira listas curtas e instruções acionáveis.

## Segurança

- Nunca vaze segredos. Nunca hardcode credenciais ou crie arquivos `.env` com chaves de API.
- Todos os segredos devem ser lidos dinamicamente do cofre em `D:\Users\charl\.secrets\keys.json`. A chave do WAHA é `waha_api_key`.
- As portas das contas WAHA são: 3000 (Charles Pessoal), 3001 (Liliane Esposa), 3002 (Marketing), 3003 (Suporte), 3004 (Sistema), 3005 (Reserva). Conexões HTTP exigem autenticação do cofre.
- O console Windows usa `CP1252`. Não use emojis em scripts de terminal (evite `UnicodeEncodeError`), prefira `[+]`, `[*]`, `[!]`. Para compatibilidade absoluta, force UTF-8 no início de qualquer script Python novo ou modificado (`sys.stdout.reconfigure(encoding='utf-8')` se `sys.platform.startswith('win')`) e defina `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` em scripts PowerShell.
- Antes de ações destrutivas (delete, reset, force push, drop), peça confirmação explícita.

## Qualidade

- Para tarefas "grandes": planeje primeiro e valide (testes/verificações) antes de concluir.
- Ao final, proponha 1 melhoria de Rule/Skill/Workflow (não aplique sem aprovação).

## Ambiente de Testes

- Ao realizar testes via HTTP/API em serviços locais no Windows host (como Flask na porta 5000 ou Uvicorn na porta 8000) e o WSL2 estiver rodando contêineres Docker em paralelo, utilize preferencialmente o IP literal `127.0.0.1` em vez de `localhost` nas URLs dos scripts para contornar problemas de conflito de portas de IPv6 no roteamento do Windows com o WSL2.
- Concorrência em SQLite: Ao implementar escritas e leituras simultâneas em processos paralelos (como Flask na porta 5000 e FastAPI na porta 8000 compartilhando o SQLite), utilize blocos try/except/finally garantindo o fechamento (session.close() or conn.close()) e o rollback() em caso de falha. Adicione commit() imediato após inserções rápidas para diminuir o tempo de lock das tabelas.
- SQLite FTS5 e RAG: Ao implementar buscas indexadas FTS5 no SQLite para português, utilize correspondência por prefixo com o curinga '_' (ex: 'consulta_') e implemente singularização básica de palavras-chave no Python (removendo plurais comuns terminados em 's' ou 'es') para contornar a falta de um lematizador embutido no SQLite.
