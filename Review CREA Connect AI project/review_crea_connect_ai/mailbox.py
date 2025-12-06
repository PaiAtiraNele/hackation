"""Mailbox helpers. This module focuses on parsing/handing off content to the analyzer.

Use a real IMAP client in production; here we simulate by passing the email body
content obtained elsewhere.
"""
from __future__ import annotations

from typing import Iterable

from .response_analyzer import analyze_response_content, ResponseAnalysis


def check_mailbox_for_response(messages: Iterable[str]) -> list[ResponseAnalysis]:
    """Process a list of email bodies and return their analyses."""

    return [analyze_response_content(body) for body in messages]
