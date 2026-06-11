"""Carrega configuração a partir do .env (com fallback para variáveis de ambiente)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env que estiver na raiz do projeto python/, se existir.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    admin_name: str  # banco usado só para criar o DB da aplicação se ele não existir

    def conninfo(self, dbname: str | None = None) -> str:
        return (
            f"host={self.host} port={self.port} "
            f"dbname={dbname or self.name} user={self.user} password={self.password}"
        )


@dataclass(frozen=True)
class ClickUpConfig:
    api_token: str
    list_id: str
    assignee_id: str


def load_db_config() -> DBConfig:
    return DBConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5436")),
        name=os.getenv("DB_NAME", "brio_diagnostico"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        admin_name=os.getenv("DB_ADMIN_NAME", "postgres"),
    )


def load_clickup_config() -> ClickUpConfig:
    return ClickUpConfig(
        api_token=os.getenv("CLICKUP_API_TOKEN", "pk_FAKE_TOKEN"),
        list_id=os.getenv("CLICKUP_LIST_ID", "900000000"),
        assignee_id=os.getenv("CLICKUP_ASSIGNEE_ID", "0"),
    )
