"""Orquestra o pipeline: ler JSON → validar → salvar no Postgres → criar tarefa.

Uso:
    python -m app.main data/leads_validos.json
    python -m app.main data/leads_invalidos.json
    LOG_LEVEL=DEBUG python -m app.main data/leads_validos.json
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import psycopg

from .clickup import ClickUpClientSimulado
from .config import load_clickup_config, load_db_config
from .database import LeadRepository
from .validators import validar_lote


def _configurar_logging() -> None:
    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, nivel, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


logger = logging.getLogger("pipeline")


def carregar_payload(caminho: str) -> list:
    """Lê o JSON de entrada (simula o recebimento do webhook do formulário).

    Aceita tanto uma lista de leads quanto um único objeto de lead.
    """
    p = Path(caminho)
    if not p.is_file():
        raise FileNotFoundError(f"arquivo de entrada não encontrado: {caminho}")
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON de entrada malformado: {exc}") from exc
    return dados if isinstance(dados, list) else [dados]


def executar(caminho_json: str) -> int:
    """Roda o pipeline completo. Retorna um exit code (0 = ok)."""
    db_cfg = load_db_config()
    clickup_cfg = load_clickup_config()

    # ---- Etapa 1: receber e validar ------------------------------------
    registros = carregar_payload(caminho_json)
    logger.info("Recebidos %d registro(s) de %s", len(registros), caminho_json)

    validos, rejeitados = validar_lote(registros)
    for r in rejeitados:
        logger.warning("Lead rejeitado (%s): %s", r.identificacao, "; ".join(r.erros))

    if not validos:
        logger.warning("Nenhum lead válido para processar.")
        _resumo(len(registros), validos, rejeitados, salvos=0, tarefas=0)
        return 0

    # ---- Etapas 2 e 3: salvar e criar tarefa ---------------------------
    repo = LeadRepository(db_cfg)
    repo.garantir_banco()
    repo.garantir_tabela()

    clickup = ClickUpClientSimulado(clickup_cfg)
    salvos = 0
    tarefas = 0
    puladas = 0

    with repo.conectar() as conn:
        for lead in validos:
            try:
                lead_id, task_existente = repo.salvar(conn, lead)
                salvos += 1
                logger.info("Lead salvo id=%d (%s)", lead_id, lead.email)
            except psycopg.Error as exc:
                logger.error("Falha ao salvar lead %s: %s", lead.email, exc)
                continue

            # Idempotência: se este lead já tinha tarefa criada num run anterior,
            # não cria outra no ClickUp (evita duplicata ao reprocessar o JSON).
            if task_existente:
                logger.info(
                    "Lead %s já possui tarefa ClickUp (%s); criação pulada.",
                    lead.email, task_existente,
                )
                puladas += 1
                continue

            # Falha no ClickUp não pode perder o lead: ele já está salvo.
            try:
                resp = clickup.criar_tarefa(lead)
                repo.marcar_tarefa_criada(conn, lead_id, resp["id"])
                tarefas += 1
            except Exception as exc:  # noqa: BLE001 - simulação não lança, mas blindamos a etapa real
                logger.error("Falha ao criar tarefa no ClickUp para %s: %s", lead.email, exc)
                repo.marcar_erro_clickup(conn, lead_id)

    _resumo(len(registros), validos, rejeitados, salvos, tarefas, puladas)
    return 0


def _resumo(recebidos, validos, rejeitados, salvos, tarefas, puladas=0) -> None:
    logger.info("──────── RESUMO ────────")
    logger.info("Recebidos ........ %d", recebidos)
    logger.info("Válidos .......... %d", len(validos))
    logger.info("Rejeitados ....... %d", len(rejeitados))
    logger.info("Salvos no banco .. %d", salvos)
    logger.info("Tarefas ClickUp .. %d (simuladas)", tarefas)
    if puladas:
        logger.info("Tarefas puladas .. %d (já existiam)", puladas)


def main() -> None:
    _configurar_logging()
    if len(sys.argv) != 2:
        print("Uso: python -m app.main <caminho_do_json>", file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(executar(sys.argv[1]))
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except psycopg.OperationalError as exc:
        logger.error("Não foi possível conectar ao Postgres: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
