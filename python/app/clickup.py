"""Etapa 3 — Criar tarefa no ClickUp (SIMULADO).

DECISÃO DE PROJETO: nenhuma requisição HTTP real é feita. Este módulo monta o
payload no formato exato da API do ClickUp e apenas o registra no log, devolvendo
uma resposta fake. Isso atende à especificação ("pode simular com print do
payload — documente a decisão") e evita depender de um workspace/token reais.

Para ir à API real, bastaria, em `criar_tarefa`, trocar o bloco de simulação por:

    import httpx
    resp = httpx.post(
        url,
        headers={"Authorization": cfg.api_token, "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

idealmente com retry/backoff para erros transitórios (429/5xx).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from .config import ClickUpConfig
from .models import LeadValidado

logger = logging.getLogger(__name__)


class ClickUpClientSimulado:
    """Cliente que monta o payload real do ClickUp mas não chama a API."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, config: ClickUpConfig):
        self._config = config

    def montar_payload(self, lead: LeadValidado) -> dict:
        """Monta o corpo de POST /list/{list_id}/task no formato da API v2."""
        descricao = (
            f"**Lead capturado pelo formulário de diagnóstico**\n\n"
            f"- **Nome:** {lead.nome}\n"
            f"- **Telefone:** {lead.telefone}\n"
            f"- **E-mail:** {lead.email}\n"
            f"- **Especialidade:** {lead.especialidade}\n"
            f"- **Principal desafio:** {lead.principal_desafio}\n\n"
            f"_Recebido em {datetime.now(timezone.utc).isoformat()}_"
        )
        return {
            "name": f"[Lead Diagnóstico] {lead.nome} — {lead.especialidade}",
            "description": descricao,
            "assignees": [int(self._config.assignee_id)] if self._config.assignee_id.isdigit() else [],
            "tags": ["lead", "diagnostico"],
            "priority": 2,  # 1=urgente, 2=alta, 3=normal, 4=baixa
            "status": "to do",
        }

    def criar_tarefa(self, lead: LeadValidado) -> dict:
        """Simula POST de uma tarefa e retorna uma resposta fake com id."""
        url = f"{self.BASE_URL}/list/{self._config.list_id}/task"
        payload = self.montar_payload(lead)

        # Mascara o token no log — nunca registrar credencial em claro.
        token_mascarado = self._config.api_token[:6] + "***REDACTED***"

        logger.info("→ [SIMULADO] POST %s", url)
        logger.info("  Authorization: %s", token_mascarado)
        logger.info("  Payload:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))

        task_id = f"sim_{uuid.uuid4().hex[:12]}"
        logger.info("← [SIMULADO] 200 OK  task id = %s", task_id)
        return {"id": task_id, "url": f"https://app.clickup.com/t/{task_id}", "simulado": True}
