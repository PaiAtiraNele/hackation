"""Configuration helpers for CREA Connect AI validation workflow."""
from __future__ import annotations

import os
from dataclasses import dataclass
@dataclass(frozen=True)
class SMTPConfig:
    """SMTP connection settings loaded from environment variables."""

    host: str
    port: int
    user: str
    password: str
    sender: str

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Build SMTP configuration from CREA_* environment variables.

        Raises:
            ValueError: If required variables are missing or malformed.
        """

        host = os.environ.get("CREA_SMTP_HOST")
        user = os.environ.get("CREA_SMTP_USER")
        password = os.environ.get("CREA_SMTP_PASSWORD")
        sender = os.environ.get("CREA_SMTP_SENDER") or user
        port_raw = os.environ.get("CREA_SMTP_PORT", "587")

        if not host or not user or not password:
            raise ValueError(
                "Missing SMTP configuration. Set CREA_SMTP_HOST, CREA_SMTP_USER and CREA_SMTP_PASSWORD."
            )

        try:
            port = int(port_raw)
        except ValueError as exc:  # noqa: TRY003 - localized validation only
            raise ValueError("CREA_SMTP_PORT must be a valid integer.") from exc

        return cls(host=host, port=port, user=user, password=password, sender=sender)


THRESHOLD_CONFIRMATION: float = 0.85
"""Confidence threshold for automatic validation acceptance."""


DEFAULT_TIMEOUT_SECONDS = 20
"""Default timeout for network operations (mail fetch / send)."""
