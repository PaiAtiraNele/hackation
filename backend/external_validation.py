import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional


THRESHOLD_CONFIRMATION = 0.85


POSITIVE_TERMS = [
    "confirmamos",
    "em conformidade",
    "dados válidos",
    "atribuições aceitas",
    "concluído com êxito",
    "válido",
    "regular",
]


NEGATIVE_TERMS = [
    "não localizamos",
    "inconsistente",
    "inválido",
    "falsificação",
    "irregular",
    "não procede",
]


PROTOCOLO_REGEX = re.compile(
    r"(protocolo|registro|valida[çc][aã]o|refer[eê]ncia|ref)[\s:#-]*([A-Z0-9/.-]{4,})",
    re.IGNORECASE,
)


def _build_email_body(solicitant_data: Dict[str, str], institution_data: Dict[str, str]) -> str:
    return f"""
Prezada(o) {institution_data.get('nome')},

O Conselho Regional de Engenharia e Agronomia do Rio Grande do Sul (CREA-RS) está conduzindo o processo de registro profissional do(a) solicitante abaixo, que apresentou um diploma/certificado emitido por Vossa Instituição.

Para dar prosseguimento ao registro de atribuições técnicas, solicitamos urgentemente a confirmação da veracidade e dos dados de conclusão do curso.

*DADOS DO SOLICITANTE PARA VALIDAÇÃO:*

* Nome Completo: {solicitant_data.get('nome')}
* CPF: {solicitant_data.get('cpf')}
* Matrícula: {solicitant_data.get('matricula')}
* Data de Nascimento: {solicitant_data.get('data_nascimento')}
* Curso/Habilitação: {solicitant_data.get('curso')}
* Carga Horária Total: {solicitant_data.get('carga_horaria')}
* Período de Conclusão: {solicitant_data.get('periodo_conclusao')}
* Data da Colação de Grau/Emissão: {solicitant_data.get('data_colacao')}

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


def send_validation_email(solicitant_data: Dict[str, str], institution_data: Dict[str, str]) -> Dict[str, str]:
    """Envia o e-mail de validação usando SMTP configurado via variáveis de ambiente.

    Em ausência de configuração SMTP, retorna um resultado simulado para demos.
    """

    smtp_host = os.environ.get("CREA_SMTP_HOST")
    smtp_port = int(os.environ.get("CREA_SMTP_PORT", "465"))
    smtp_user = os.environ.get("CREA_SMTP_USER")
    smtp_pass = os.environ.get("CREA_SMTP_PASS")
    sender_email = os.environ.get("CREA_SMTP_FROM") or smtp_user or "noreply@crea-rs.gov.br"

    subject = f"URGENTE: Solicitação de Confirmação de Dados para Registro Profissional CREA-RS (Ref: {solicitant_data.get('cpf')})"
    body = _build_email_body(solicitant_data, institution_data)

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = institution_data.get("email")
    message.attach(MIMEText(body, "plain", "utf-8"))

    if not smtp_host:
        return {
            "sent": False,
            "simulado": True,
            "preview_subject": subject,
            "preview_body": body,
            "destinatario": institution_data.get("email"),
            "motivo": "Variáveis de ambiente SMTP ausentes."
        }

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, [institution_data.get("email")], message.as_string())
    except Exception as exc:  # pragma: no cover - protegido para ambientes demo
        return {
            "sent": False,
            "simulado": True,
            "erro": str(exc),
            "preview_subject": subject,
            "preview_body": body,
            "destinatario": institution_data.get("email"),
        }

    return {"sent": True, "simulado": False, "destinatario": institution_data.get("email"), "assunto": subject}


def check_mailbox_for_response() -> Dict[str, str]:
    """Simula busca de respostas na caixa postal.

    Em produção, esta função poderia usar IMAP para ler a caixa da organização.
    """

    resposta_mock = (
        "Confirmamos a autenticidade do diploma informado. Protocolo interno PR-4581/2024."  # noqa: E501
    )
    return {"encontrado": True, "corpo": resposta_mock}


def analyze_response_content(email_body: str) -> Dict[str, Optional[str]]:
    body_lower = email_body.lower()

    positivos = [term for term in POSITIVE_TERMS if term in body_lower]
    negativos = [term for term in NEGATIVE_TERMS if term in body_lower]

    match = PROTOCOLO_REGEX.search(email_body)
    protocolo = match.group(2) if match else None

    score = 0.5
    score += min(0.4, 0.1 * len(positivos))
    score -= min(0.4, 0.1 * len(negativos))
    if protocolo:
        score += 0.05
    score = max(0.0, min(1.0, score))

    status = "CONFIRMADO" if score >= THRESHOLD_CONFIRMATION else "INCONGRUENTE"
    resultado = {
        "status": status,
        "score": round(score, 2),
        "protocolo_encontrado": protocolo,
    }
    if status == "INCONGRUENTE":
        resultado["motivo"] = "Termos negativos ou ambíguos" if negativos else "Score insuficiente"

    return resultado


def process_validation_result(analysis_result: Dict[str, Optional[str]], solicitant_id: str) -> Dict[str, str]:
    score = analysis_result.get("score", 0)
    status = analysis_result.get("status") or "INCONGRUENTE"

    if score >= THRESHOLD_CONFIRMATION and status == "CONFIRMADO":
        return {
            "status_interno": "validado",
            "registro_automatico": True,
            "notificacao_solicitante": "Validação da Instituição Recebida e Confirmada.",
            "referencia": analysis_result.get("protocolo_encontrado"),
            "solicitante": solicitant_id,
        }

    return {
        "status_interno": "revisao_humana",
        "registro_automatico": False,
        "alerta": f"Atenção: Validação de {solicitant_id} requer análise manual. Score: {score}.",
        "motivo": analysis_result.get("motivo") or "Score abaixo do limiar",
        "solicitante": solicitant_id,
    }
