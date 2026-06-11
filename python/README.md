# Pipeline de Diagnóstico — Brio

Script Python que captura leads de um formulário de diagnóstico, valida e trata os
dados, salva no Postgres e cria uma tarefa no ClickUp para o time comercial.

São as três etapas pedidas na especificação:

1. **Receber e validar** — lê um JSON (simula o webhook do formulário), valida
   campos obrigatórios, normaliza nome/e-mail e formata o telefone para E.164.
2. **Salvar em banco** — insere os dados tratados no Postgres (tabela
   `diagnostico_leads`).
3. **Criar tarefa via API** — monta o payload da API do ClickUp e cria a tarefa
   **(simulado — ver decisão abaixo)**.

## Estrutura

```
python/
├── app/
│   ├── main.py         # orquestra o pipeline
│   ├── config.py       # carrega .env
│   ├── models.py       # LeadValidado / LeadRejeitado
│   ├── validators.py   # Etapa 1
│   ├── database.py     # Etapa 2 (psycopg 3)
│   └── clickup.py      # Etapa 3 (cliente simulado)
├── data/
│   ├── leads_validos.json
│   └── leads_invalidos.json
├── tests/test_validators.py
├── requirements.txt
└── .env.example
```

## Como rodar

### 1. Subir o Postgres

```bash
cd python
docker compose up -d
```

> Já tem algo na porta 5436? Troque o mapeamento em `docker-compose.yml`
> (ex.: `"5437:5432"`) e ajuste `DB_PORT` no `.env`.

### 2. Rodar o script

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Caso feliz (3 leads válidos)
python -m app.main data/leads_validos.json

# Casos de erro (validação rejeita cada lead com os motivos)
python -m app.main data/leads_invalidos.json

# Ver o payload do ClickUp em detalhe
LOG_LEVEL=DEBUG python -m app.main data/leads_validos.json
```

### Conferir os dados salvos

```bash
docker exec brio-diagnostico-postgres \
  psql -U postgres -d brio_diagnostico \
  -c "SELECT id, nome, email, telefone, status, clickup_task_id FROM diagnostico_leads;"
```

### Testes

```bash
cd python && pytest tests/
```

## Banco de dados

O Postgres sobe via `docker compose up -d` (container `brio-diagnostico-postgres`,
exposto em `localhost:5436`). O script cria, de forma idempotente, o banco
`brio_diagnostico` e a tabela `diagnostico_leads`. O e-mail é `UNIQUE` e a inserção
usa `ON CONFLICT DO UPDATE`, então reprocessar o mesmo JSON **não duplica** leads.

## Decisão: ClickUp simulado

A chamada à API do ClickUp é **simulada** — nenhum HTTP real é disparado. O módulo
`app/clickup.py` monta o payload exatamente no formato de
`POST /api/v2/list/{list_id}/task` (name, description em markdown, assignees, tags,
priority), registra o request no log (com o token mascarado) e devolve uma resposta
fake com um `id`. A especificação permite explicitamente isso ("pode simular com
print do payload — documente a decisão").

Para ir à API real: definir `CLICKUP_API_TOKEN`/`CLICKUP_LIST_ID` válidos e trocar o
bloco de simulação em `criar_tarefa` por uma chamada `httpx.post(...)` com
`raise_for_status()` e retry/backoff em erros transitórios (429/5xx). O passo a
passo está documentado na docstring de `app/clickup.py`.

## Tratamento de erros

- **JSON ausente/malformado** → aborta com mensagem clara e exit code 1.
- **Lead inválido** → rejeita apenas aquele lead (acumulando todos os motivos) e
  segue processando os demais; nada inválido chega ao banco.
- **Erro de banco** num lead → rollback e segue para o próximo.
- **Falha no ClickUp** → o lead permanece salvo com `status = 'erro_clickup'`; o
  dado nunca se perde por causa da etapa seguinte.
- Ao final, um resumo mostra recebidos / válidos / rejeitados / salvos / tarefas.
