"""Testes da Etapa 1 (validação e normalização)."""

import sys
from pathlib import Path

# Permite rodar `pytest` a partir de python/ sem instalar o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.models import LeadRejeitado, LeadValidado
from app.validators import (
    normalizar_email,
    normalizar_telefone,
    validar_lead,
    validar_lote,
)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("(11) 98765-4321", "+5511987654321"),
        ("+55 21 3344-5566", "+552133445566"),
        ("31987654321", "+5531987654321"),
        ("011 98765-4321", "+5511987654321"),  # 0 de discagem (celular, 12 díg.)
        ("011 3344-5566", "+551133445566"),     # 0 de discagem (fixo, 11 díg.)
        ("5511987654321", "+5511987654321"),    # já com código do país
    ],
)
def test_normalizar_telefone_valido(entrada, esperado):
    telefone, erro = normalizar_telefone(entrada)
    assert erro is None
    assert telefone == esperado


@pytest.mark.parametrize("entrada", ["", "1234", "abc", "999"])
def test_normalizar_telefone_invalido(entrada):
    telefone, erro = normalizar_telefone(entrada)
    assert telefone is None
    assert erro is not None


def test_normalizar_email():
    assert normalizar_email("  ANA.Beatriz@Clinica.com.BR ") == "ana.beatriz@clinica.com.br"


def test_lead_valido_e_normalizado():
    resultado = validar_lead(
        {
            "nome": "  ana   beatriz souza ",
            "telefone": "(11) 98765-4321",
            "email": "ANA@Clinica.com ",
            "especialidade": " Dermatologia ",
            "principal_desafio": "Agenda  ociosa",
        }
    )
    assert isinstance(resultado, LeadValidado)
    assert resultado.nome == "Ana Beatriz Souza"
    assert resultado.telefone == "+5511987654321"
    assert resultado.email == "ana@clinica.com"
    assert resultado.especialidade == "Dermatologia"
    assert resultado.principal_desafio == "Agenda ociosa"


def test_acumula_multiplos_erros():
    resultado = validar_lead(
        {
            "nome": "",
            "telefone": "1234",
            "email": "invalido",
            "especialidade": "",
            "principal_desafio": "",
        }
    )
    assert isinstance(resultado, LeadRejeitado)
    # nome vazio + especialidade vazia + desafio vazio + email ruim + telefone curto
    assert len(resultado.erros) >= 5


def test_email_malformado_rejeitado():
    resultado = validar_lead(
        {
            "nome": "Mariana",
            "telefone": "11999998888",
            "email": "mariana(arroba)email.com",
            "especialidade": "Pediatria",
            "principal_desafio": "Retenção",
        }
    )
    assert isinstance(resultado, LeadRejeitado)
    assert any("e-mail" in e for e in resultado.erros)


def test_validar_lote_separa_validos_e_rejeitados():
    validos, rejeitados = validar_lote(
        [
            {
                "nome": "Carlos",
                "telefone": "+55 21 3344-5566",
                "email": "carlos@x.com",
                "especialidade": "Ortopedia",
                "principal_desafio": "Fidelização",
            },
            {"nome": "Incompleto"},
        ]
    )
    assert len(validos) == 1
    assert len(rejeitados) == 1
