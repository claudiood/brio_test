"""Etapa 1 — Receber e validar.

Valida campos obrigatórios, normaliza nome/e-mail e formata o telefone para o
padrão E.164 brasileiro (+55DDDNÚMERO). A validação acumula TODOS os erros de
cada lead antes de rejeitá-lo, evitando o ciclo "corrige um erro, aparece outro".
"""

from __future__ import annotations

import re

from .models import CAMPOS_OBRIGATORIOS, LeadRejeitado, LeadValidado

# Regex pragmática para e-mail: algo@dominio.tld (não cobre 100% da RFC,
# mas barra os erros comuns de digitação que quebram automações).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar_texto(valor: object) -> str:
    """Remove espaços nas pontas e colapsa espaços internos múltiplos."""
    return re.sub(r"\s+", " ", str(valor or "").strip())


def normalizar_email(valor: object) -> str:
    return str(valor or "").strip().lower()


def normalizar_telefone(valor: object) -> tuple[str | None, str | None]:
    """Normaliza um telefone brasileiro para E.164.

    Retorna (telefone_normalizado, None) em sucesso, ou (None, motivo) em falha.
    Aceita formatos variados: (11) 98765-4321, +55 11 98765-4321, 11987654321.
    """
    digitos = re.sub(r"\D", "", str(valor or ""))

    # Remove o código do país, se já vier com 55 na frente.
    if len(digitos) > 11 and digitos.startswith("55"):
        digitos = digitos[2:]
    # Remove um eventual 0 de discagem antes do DDD (ex.: 011..., 01133...).
    # DDD nunca começa com 0, então um 0 inicial em 11/12 dígitos é discagem.
    if len(digitos) in (11, 12) and digitos.startswith("0"):
        digitos = digitos[1:]

    if len(digitos) not in (10, 11):
        return None, (
            "telefone inválido: esperado DDD + número (10 ou 11 dígitos), "
            f"recebido {len(digitos)} dígito(s)"
        )
    return f"+55{digitos}", None


def validar_lead(bruto: object) -> LeadValidado | LeadRejeitado:
    """Valida um único registro de lead, acumulando todos os erros encontrados."""
    erros: list[str] = []

    if not isinstance(bruto, dict):
        return LeadRejeitado(bruto={"_raw": bruto}, erros=["registro não é um objeto JSON"])

    # Campos obrigatórios: presença e não-vazio (após strip).
    for campo in CAMPOS_OBRIGATORIOS:
        if not str(bruto.get(campo, "") or "").strip():
            erros.append(f"campo obrigatório ausente ou vazio: '{campo}'")

    email = normalizar_email(bruto.get("email"))
    if email and not _EMAIL_RE.match(email):
        erros.append(f"e-mail malformado: '{email}'")

    telefone, erro_tel = normalizar_telefone(bruto.get("telefone"))
    # Só reporta erro de formato se o campo não estava já marcado como vazio.
    if erro_tel and str(bruto.get("telefone", "") or "").strip():
        erros.append(erro_tel)

    if erros:
        return LeadRejeitado(bruto=bruto, erros=erros)

    return LeadValidado(
        nome=_normalizar_texto(bruto.get("nome")).title(),
        telefone=telefone or "",
        email=email,
        especialidade=_normalizar_texto(bruto.get("especialidade")),
        principal_desafio=_normalizar_texto(bruto.get("principal_desafio")),
    )


def validar_lote(registros: list) -> tuple[list[LeadValidado], list[LeadRejeitado]]:
    """Valida uma lista de registros, separando válidos de rejeitados."""
    validos: list[LeadValidado] = []
    rejeitados: list[LeadRejeitado] = []
    for bruto in registros:
        resultado = validar_lead(bruto)
        if isinstance(resultado, LeadValidado):
            validos.append(resultado)
        else:
            rejeitados.append(resultado)
    return validos, rejeitados
