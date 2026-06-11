"""Modelos de dados do pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


# Campos obrigatórios esperados no payload do formulário.
CAMPOS_OBRIGATORIOS = ("nome", "telefone", "email", "especialidade", "principal_desafio")


@dataclass
class LeadValidado:
    """Lead já validado e normalizado, pronto para persistir."""

    nome: str
    telefone: str  # E.164, ex.: +5511987654321
    email: str
    especialidade: str
    principal_desafio: str


@dataclass
class LeadRejeitado:
    """Lead que falhou na validação, com a lista de motivos acumulados."""

    bruto: dict
    erros: list[str] = field(default_factory=list)

    @property
    def identificacao(self) -> str:
        # Tenta dar um rótulo amigável para o log mesmo com dados sujos.
        return str(self.bruto.get("nome") or self.bruto.get("email") or "<sem nome>").strip()
