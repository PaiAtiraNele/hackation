"""CREA Connect AI validation toolkit."""
from .config import SMTPConfig, THRESHOLD_CONFIRMATION, DEFAULT_TIMEOUT_SECONDS
from .decision import process_validation_result
from .email_sender import send_validation_email
from .response_analyzer import analyze_response_content, ResponseAnalysis

__all__ = [
    "SMTPConfig",
    "THRESHOLD_CONFIRMATION",
    "DEFAULT_TIMEOUT_SECONDS",
    "process_validation_result",
    "send_validation_email",
    "analyze_response_content",
    "ResponseAnalysis",
]
