"""Etapa 2 — Salvar no Postgres.

Repositório fino sobre o psycopg 3. Faz bootstrap idempotente (cria o banco da
aplicação e a tabela se não existirem) e insere leads com ON CONFLICT no e-mail,
de modo que reprocessar o mesmo JSON não gera duplicatas.
"""

from __future__ import annotations

import logging

import psycopg

from .config import DBConfig
from .models import LeadValidado

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS diagnostico_leads (
    id                BIGSERIAL PRIMARY KEY,
    nome              TEXT NOT NULL,
    telefone          TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    especialidade     TEXT NOT NULL,
    principal_desafio TEXT NOT NULL,
    clickup_task_id   TEXT,
    status            TEXT NOT NULL DEFAULT 'novo',
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_UPSERT_SQL = """
INSERT INTO diagnostico_leads
    (nome, telefone, email, especialidade, principal_desafio, status)
VALUES
    (%(nome)s, %(telefone)s, %(email)s, %(especialidade)s, %(principal_desafio)s, 'novo')
ON CONFLICT (email) DO UPDATE SET
    nome              = EXCLUDED.nome,
    telefone          = EXCLUDED.telefone,
    especialidade     = EXCLUDED.especialidade,
    principal_desafio = EXCLUDED.principal_desafio
RETURNING id, clickup_task_id
"""


class LeadRepository:
    """Acesso à tabela diagnostico_leads."""

    def __init__(self, config: DBConfig):
        self._config = config

    def garantir_banco(self) -> None:
        """Cria o banco da aplicação se ainda não existir.

        CREATE DATABASE não roda dentro de transação, por isso conecta-se ao
        banco administrativo em autocommit só para esta verificação.
        """
        with psycopg.connect(
            self._config.conninfo(self._config.admin_name), autocommit=True
        ) as conn:
            existe = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (self._config.name,)
            ).fetchone()
            if existe:
                logger.debug("Banco '%s' já existe.", self._config.name)
                return
            # Identificador não pode ser parametrizado; o nome vem da config, não do usuário.
            conn.execute(f'CREATE DATABASE "{self._config.name}"')
            logger.info("Banco '%s' criado.", self._config.name)

    def garantir_tabela(self) -> None:
        with psycopg.connect(self._config.conninfo()) as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()
        logger.debug("Tabela diagnostico_leads pronta.")

    def conectar(self) -> psycopg.Connection:
        return psycopg.connect(self._config.conninfo())

    @staticmethod
    def salvar(conn: psycopg.Connection, lead: LeadValidado) -> tuple[int, str | None]:
        """Insere/atualiza um lead. Commit por lead (isola falhas).

        Retorna (id, clickup_task_id). O task_id vem preenchido quando o lead já
        existia e já tinha tarefa criada num run anterior — o que permite ao
        chamador evitar criar uma tarefa duplicada no ClickUp.
        """
        try:
            row = conn.execute(
                _UPSERT_SQL,
                {
                    "nome": lead.nome,
                    "telefone": lead.telefone,
                    "email": lead.email,
                    "especialidade": lead.especialidade,
                    "principal_desafio": lead.principal_desafio,
                },
            ).fetchone()
            conn.commit()
            return int(row[0]), row[1]
        except psycopg.Error:
            conn.rollback()
            raise

    @staticmethod
    def marcar_tarefa_criada(conn: psycopg.Connection, lead_id: int, task_id: str) -> None:
        conn.execute(
            "UPDATE diagnostico_leads SET clickup_task_id = %s, status = 'tarefa_criada' "
            "WHERE id = %s",
            (task_id, lead_id),
        )
        conn.commit()

    @staticmethod
    def marcar_erro_clickup(conn: psycopg.Connection, lead_id: int) -> None:
        conn.execute(
            "UPDATE diagnostico_leads SET status = 'erro_clickup' WHERE id = %s",
            (lead_id,),
        )
        conn.commit()
