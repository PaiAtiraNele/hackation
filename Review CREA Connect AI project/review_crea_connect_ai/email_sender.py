"""Email automation module for CREA-RS validation requests."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .config import SMTPConfig, DEFAULT_TIMEOUT_SECONDS
from .data_models import InstitutionData, SolicitationData
from .email_templates import EMAIL_SUBJECT_TEMPLATE, build_email_body


class EmailDeliveryError(RuntimeError):
    """Raised when an SMTP delivery fails."""


def send_validation_email(
    solicitant_data: SolicitationData,
    institution_data: InstitutionData,
    *,
    smtp_config: Optional[SMTPConfig] = None,
    custom_sender: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Send a validation email to the institution contact.

    Args:
        solicitant_data: Data about the professional solicitation.
        institution_data: Contact data for the issuing institution.
        smtp_config: Optional pre-built SMTP configuration (defaults to env lookup).
        custom_sender: Optional sender email to override environment default.
        timeout: SMTP connection timeout in seconds.

    Returns:
        The message ID string as reported by the SMTP server (if available).

    Raises:
        ValueError: If the SMTP configuration is incomplete.
        EmailDeliveryError: If the SMTP operation fails.
    """

    config = smtp_config or SMTPConfig.from_env()
    sender = custom_sender or config.sender

    subject = EMAIL_SUBJECT_TEMPLATE.format(cpf=solicitant_data.cpf_sanitized())
    body = build_email_body(solicitant_data, institution_data)

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = institution_data.email_contato
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(config.host, config.port, timeout=timeout) as smtp:
            smtp.starttls()
            smtp.login(config.user, config.password)
            response = smtp.send_message(message)
    except Exception as exc:  # noqa: BLE001 - propagate as domain-specific error
        raise EmailDeliveryError(f"Falha ao enviar e-mail: {exc}") from exc

    return str(response)
