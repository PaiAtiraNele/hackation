"""NLP-like analyzer for institutional email responses."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

POSITIVE_TERMS: Sequence[str] = (
    "confirmamos",
    "em conformidade",
    "dados válidos",
    "atribuições aceitas",
    "concluído com êxito",
    "válido",
    "procedente",
)
NEGATIVE_TERMS: Sequence[str] = (
    "não localizamos",
    "inconsistente",
    "inválido",
    "falsificação",
    "não corresponde",
    "não procede",
)
PROTOCOL_REGEX = re.compile(r"(protocolo|registro|refer[êe]ncia)[:\s]*([A-Z0-9-]{4,})", re.IGNORECASE)


@dataclass(frozen=True)
class ResponseAnalysis:
    status: str
    score: float
    protocolo_encontrado: str | None = None
    motivo: str | None = None


def _term_hits(body: str, terms: Iterable[str]) -> List[str]:
    lowered = body.lower()
    return [term for term in terms if term in lowered]


def _extract_protocol(body: str) -> str | None:
    match = PROTOCOL_REGEX.search(body)
    if not match:
        return None
    return match.group(2)


def analyze_response_content(email_body: str) -> ResponseAnalysis:
    """Analyze the institution response and compute a confirmation score."""

    positives = _term_hits(email_body, POSITIVE_TERMS)
    negatives = _term_hits(email_body, NEGATIVE_TERMS)
    protocol = _extract_protocol(email_body)

    base_score = len(positives) * 0.2
    if protocol:
        base_score += 0.2
    if negatives:
        base_score -= len(negatives) * 0.25

    score = max(0.0, min(base_score, 1.0))

    if score >= 0.85 and not negatives:
        status = "CONFIRMADO"
        motivo = None
    elif negatives and score < 0.5:
        status = "INCONGRUENTE"
        motivo = "Termos negativos ou ambíguos"
    else:
        status = "REVISAR"
        motivo = "Score intermediário; revisão manual recomendada"

    return ResponseAnalysis(
        status=status,
        score=round(score, 2),
        protocolo_encontrado=protocol,
        motivo=motivo,
    )
