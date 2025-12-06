"""Email subject/body templates for CREA-RS validation."""
from __future__ import annotations

from .data_models import InstitutionData, SolicitationData

EMAIL_SUBJECT_TEMPLATE = (
    "URGENTE: Solicitação de Confirmação de Dados para Registro Profissional CREA-RS (Ref: {cpf})"
)


def build_email_body(solicitant_data: SolicitationData, institution_data: InstitutionData) -> str:
    """Build the enhanced validation template populated with requester data."""

    return f"""
Prezada(o) {institution_data.nome},

O Conselho Regional de Engenharia e Agronomia do Rio Grande do Sul (CREA-RS) está conduzindo o processo de registro profissional do(a) solicitante abaixo, que apresentou um diploma/certificado emitido por Vossa Instituição.

Para dar prosseguimento ao registro de atribuições técnicas, solicitamos urgentemente a confirmação da veracidade e dos dados de conclusão do curso.

DADOS DO SOLICITANTE PARA VALIDAÇÃO:

* Nome Completo: {solicitant_data.nome_completo}
* CPF: {solicitant_data.cpf}
* Matrícula: {solicitant_data.matricula}
* Curso/Habilitação: {solicitant_data.curso}
* Carga Horária Total: {solicitant_data.carga_horaria}
* Período de Conclusão: {solicitant_data.periodo_conclusao}
* Data da Colação de Grau/Emissão: {solicitant_data.data_colacao}

A confirmação por e-mail, de forma clara e objetiva, é suficiente para a validação no nosso sistema.

Solicitamos, preferencialmente, o envio do Número de Registro ou Código de Validação Digital do diploma, se disponível.

Certos de sua colaboração para a rápida inserção de novos profissionais no mercado, agradecemos a atenção.

Atenciosamente,

Núcleo de Habilitação e Registro Profissional
Conselho Regional de Engenharia e Agronomia do Rio Grande do Sul (CREA-RS)
Endereço Sede: [Rua e Número, Bairro]
Cidade/UF: Porto Alegre/RS
Telefone: [Telefone do CREA-RS]
"""
