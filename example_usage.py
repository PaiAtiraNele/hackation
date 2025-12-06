"""Example orchestration for the CREA-RS validation automation workflow."""
from validation_automation import (
    InstitutionData,
    SolicitationData,
    analyze_response_content,
    process_validation_result,
)


if __name__ == "__main__":
    solicitant = SolicitationData(
        nome_completo="Fulano de Tal",
        cpf="123.456.789-00",
        data_nascimento="01/01/1990",
        matricula="2023ABC",
        curso="Engenharia Civil",
        carga_horaria="3.600h",
        periodo_conclusao="01/2016 a 12/2020",
        data_colacao="15/12/2020",
    )
    institution = InstitutionData(nome="Universidade Exemplo", email_contato="contato@universidade.br")

    # A chamada real de e-mail depende de variáveis de ambiente de SMTP configuradas:
    # send_validation_email(solicitant, institution)

    resposta = """
    Confirmamos a validade dos dados apresentados. O registro foi concluído com êxito.
    Protocolo: ABC-1234
    """
    analise = analyze_response_content(resposta)
    decisao = process_validation_result(analise, solicitant_id="REQ-99", solicitant_name=solicitant.nome_completo)

    print("Análise:", analise)
    print("Decisão:", decisao)
