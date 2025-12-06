"""Business logic for CREA-RS validation decisions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol

from .config import THRESHOLD_CONFIRMATION
from .response_analyzer import ResponseAnalysis


@dataclass(frozen=True)
class DecisionOutcome:
    status: str
    message: str
    alerts: Dict[str, str] | None = None


class Notifier(Protocol):
    def notify(self, target: str, message: str) -> None:  # pragma: no cover - interface only
        ...


class InMemoryNotifier:
    """Simple notifier that accumulates messages for inspection."""

    def __init__(self) -> None:
        self.sent: Dict[str, str] = {}

    def notify(self, target: str, message: str) -> None:
        self.sent[target] = message


def process_validation_result(
    analysis_result: ResponseAnalysis,
    solicitant_id: str,
    solicitant_name: str,
    notifier: Notifier | None = None,
) -> DecisionOutcome:
    """Apply CREA-RS business rules to the analyzed response."""

    effective_notifier = notifier or InMemoryNotifier()

    if analysis_result.score >= THRESHOLD_CONFIRMATION and analysis_result.status == "CONFIRMADO":
        msg = "Validação da Instituição Recebida e Confirmada."
        effective_notifier.notify(solicitant_id, msg)
        return DecisionOutcome(status="AUTOMATICO", message=msg)

    alert = (
        f"Atenção: Validação de {solicitant_name} requer análise manual. "
        f"Score: {analysis_result.score}."
    )
    effective_notifier.notify("dashboard", alert)
    return DecisionOutcome(
        status="REVISAO_MANUAL",
        message=alert,
        alerts={"solicitant_id": solicitant_id, "motivo": analysis_result.motivo or "score baixo"},
    )
