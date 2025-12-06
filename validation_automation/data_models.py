"""Data models for the CREA-RS validation automation workflow."""
from dataclasses import dataclass


@dataclass
class SolicitationData:
    """Structured data for a professional registration solicitation."""

    nome_completo: str
    cpf: str
    data_nascimento: str
    matricula: str
    curso: str
    carga_horaria: str
    periodo_conclusao: str
    data_colacao: str


@dataclass
class InstitutionData:
    """Minimal institution contact data required for validation."""

    nome: str
    email_contato: str
