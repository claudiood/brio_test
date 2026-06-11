# brio_test

## Desafio 1 — Automação no n8n

A automação foi montada no n8n para receber os dados de uma tarefa, checar o status, gerar as hashtags, salva-los no sheets, encaminhando ao final uma notificação pro time. O fluxo completo está nas imagens da pasta `n8n/`.

### Decisões de simulação

Duas integrações foram **simuladas** por falta de acesso às credenciais reais no ambiente:

- **ClickUp** — não havia acesso às credenciais do ClickUp dentro do n8n, então os dados da tarefa foram simulados a partir de um **payload construído manualmente**, representando a resposta que a API do ClickUp devolveria. Isso permitiu seguir com o restante do fluxo sem depender de um workspace/token reais.
- **Notificação (Evolution API)** — o envio da notificação também foi simulado, pois não havia as credenciais da Evolution API. O passo está montado e documentado, apenas sem disparo real.

### O que está funcionando de fato

Apesar das duas simulações acima, o núcleo da automação está **operacional de ponta a ponta**:

1. **Obter os dados** da tarefa a partir do payload de entrada.
2. **Checar o status da tarefa**.
3. **Gerar as hashtags** utilizando IA.
4. **Montar o registro** organizar os dados para salvar.
5. **Salvar em uma planilha no Google Sheets**.

A persistência foi feita no **Google Sheets** por uma escolha prática: as credenciais próprias já estavam disponíveis.

## Desafio 2 — Pipeline em Python

O script recebe os leads de um formulário de diagnóstico, valida e trata os dados, persiste em banco e cria uma tarefa para o time comercial. O código, instruções de execução e detalhes técnicos estão em [`python/`](./python) (ver [`python/README.md`](./python/README.md)).

O pipeline cobre as três etapas pedidas:

1. **Receber e validar** — lê um JSON (simula o webhook do formulário), valida campos obrigatórios, normaliza nome/e-mail e formata o telefone para o padrão E.164.
2. **Salvar em banco** — insere os dados tratados no **PostgreSQL**, escolhido por já estar disponível no ambiente.
3. **Criar tarefa via API** — monta o payload para simular o recebimento dos dados da API do ClickUp e cria a tarefa.

### Decisões de simulação

- **ClickUp** — assim como no Desafio 1, a chamada à API do ClickUp é **simulada**: a aplicação monta o payload e **simula o retorno dos dados da requisição** (resposta com `id` da tarefa), sem disparar HTTP real, por não haver credenciais reais. A decisão está documentada em `python/README.md`.

### Status

Tudo está **funcional**: validação, persistência no Postgres e o fluxo de criação de tarefa simulada rodam de ponta a ponta. O projeto inclui testes automatizados e tratamento de erros que garante que um lead inválido ou uma falha pontual não interrompam o processamento dos demais nem percam dados.

Pontos de robustez adicionais:

- **Idempotência** — reprocessar o mesmo JSON não duplica leads (upsert por e-mail no banco) nem tarefas no ClickUp.
- **Testes automatizados** — a etapa de validação/normalização é coberta por testes para garantir o funcionamento.
- **Resiliência** — um lead nunca se perde por falha em uma etapa seguinte.
