"""Dataclasses for solicitation and institution details."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class InstitutionData:
    nome: str
    email_contato: str


@dataclass(frozen=True)
class SolicitationData:
    nome_completo: str
    cpf: str
    data_nascimento: Optional[date]
    matricula: str
    curso: str
    carga_horaria: str
    periodo_conclusao: str
    data_colacao: str

    def cpf_sanitized(self) -> str:
        """Return only digits for CPF, helpful for subject lines."""

        return "".join(ch for ch in self.cpf if ch.isdigit())
