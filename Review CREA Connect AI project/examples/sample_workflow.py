"""Demonstration of the CREA Connect AI validation workflow."""
from __future__ import annotations

from review_crea_connect_ai.config import SMTPConfig
from review_crea_connect_ai.data_models import InstitutionData, SolicitationData
from review_crea_connect_ai.decision import process_validation_result, InMemoryNotifier
from review_crea_connect_ai.mailbox import check_mailbox_for_response
from review_crea_connect_ai.response_analyzer import analyze_response_content


if __name__ == "__main__":
    solicitant = SolicitationData(
        nome_completo="Fulana de Tal",
        cpf="123.456.789-00",
        data_nascimento=None,
        matricula="2024-001",
        curso="Engenharia Civil",
        carga_horaria="3600h",
        periodo_conclusao="01/2020 a 12/2023",
        data_colacao="15/12/2023",
    )
    institution = InstitutionData(nome="Universidade X", email_contato="registro@universidadex.br")

    # Sending would require valid environment credentials; omitted in demo.
    # smtp_config = SMTPConfig.from_env()
    # send_validation_email(solicitant, institution, smtp_config=smtp_config)

    resposta = """
    Confirmamos que os dados apresentados estão em conformidade. Protocolo: ABCD-9999.
    """

    analysis = analyze_response_content(resposta)
    notifier = InMemoryNotifier()
    decision = process_validation_result(analysis, solicitant_id="S123", solicitant_name=solicitant.nome_completo, notifier=notifier)

    print("Análise:", analysis)
    print("Decisão:", decision)
    print("Notificações:", notifier.sent)
