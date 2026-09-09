# Publicação e continuidade do Kabbalah

## Repositório público

Este repositório contém apresentação do produto, código revisado, documentação
geral, exemplos sem credenciais e testes reproduzíveis. O estado alpha e os limites
conhecidos devem permanecer explícitos.

Uma publicação de documentação não implica que mudanças de um ambiente privado
foram revisadas, incorporadas ou instaladas. Cada versão de software precisa de
seu próprio conjunto de verificações.

## Documentação privada da instalação

Manter fora do repositório público:

- Inventário do equipamento e detalhes da rede, acesso e operação.
- Decisões do proprietário e fontes privadas da pesquisa.
- Registros de implantação, incidentes, backups e pendências específicas.
- Conhecimento consolidado a partir de sessões privadas.
- Artefatos de execução, bancos de estado e logs particulares.

Branches, pastas, issues e wikis de um repositório público **não são áreas
privadas**. Usar um destino separado com controle de acesso para os registros
privados. Nunca publicar senhas, tokens, chaves, sessões autenticadas ou conteúdo
de cofres — nem mesmo em um repositório privado.

## Continuidade verificável

O registro de continuidade deve identificar decisão, fonte, data, implementação,
evidência de validação e pendência. Separar requisito de implementação e teste de
conexão de teste de orquestração. Uma decisão substituída deve permanecer rastreável.

A skill `session-knowledge` pode compilar fontes selecionadas em conhecimento
com proveniência. Uma base só pode ser considerada pronta para consulta depois
de `build` e `validate --ready`. Esse resultado valida a consistência da base
importada; não prova que todo o histórico do projeto foi importado.

## Antes de publicar

- Revisar o diff e o destino público ou privado.
- Escanear segredos no histórico completo e nos arquivos novos.
- Usar apenas arquivos selecionados; não fazer upload de uma pasta de trabalho inteira.
- Preservar as fontes privadas e os backups fora do disco de trabalho principal.
- Registrar o commit publicado e os limites das verificações executadas.
