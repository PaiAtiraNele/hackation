"""Email response simulation and analysis module."""
import re
from typing import Dict, List, Optional

POSITIVE_TERMS: List[str] = [
    r"confirmamos",
    r"em conformidade",
    r"dados válidos",
    r"atribu[ií]ções aceitas",
    r"concluído com êxito",
]

NEGATIVE_TERMS: List[str] = [
    r"não localizamos",
    r"inconsistente",
    r"inválido",
    r"falsificaç[aã]o",
]

PROTOCOL_PATTERN = re.compile(
    r"(?:protocolo|registro|validaç[aã]o|validacao)[^\w]?[:#\-\s]*([A-Za-z0-9\-]{4,})",
    re.IGNORECASE,
)


def check_mailbox_for_response() -> Optional[str]:
    """Simulate mailbox polling and return a sample email body.

    In a production scenario, this function can be extended to read messages from an
    IMAP inbox. Here we return ``None`` by default to focus on the NLP pipeline.
    """

    return None


def _normalize_text(email_body: str) -> str:
    return re.sub(r"\s+", " ", email_body.strip())


def analyze_response_content(email_body: str) -> Dict[str, object]:
    """Analyze the response email body to infer validation status.

    Args:
        email_body: Raw text from the institution response.

    Returns:
        A dictionary containing the inferred status, score, protocol if found, and
        rationale for incongruent responses.
    """

    normalized_body = _normalize_text(email_body).lower()

    positive_hits = [term for term in POSITIVE_TERMS if re.search(term, normalized_body)]
    negative_hits = [term for term in NEGATIVE_TERMS if re.search(term, normalized_body)]

    protocol_match = PROTOCOL_PATTERN.search(normalized_body)
    protocolo_encontrado = protocol_match.group(1) if protocol_match else None

    base_score = 0.4
    score = base_score + (len(positive_hits) * 0.25) - (len(negative_hits) * 0.3)
    score = max(0.0, min(1.0, round(score, 3)))

    if positive_hits and not negative_hits:
        status = "CONFIRMADO"
        motivo = None
    elif negative_hits and not positive_hits:
        status = "INCONGRUENTE"
        motivo = "Termos negativos encontrados"
    else:
        status = "INCONGRUENTE"
        motivo = "Termos positivos ausentes ou resposta ambígua"

    result: Dict[str, object] = {
        "status": status,
        "score": score,
        "protocolo_encontrado": protocolo_encontrado,
    }

    if motivo:
        result["motivo"] = motivo

    if positive_hits:
        result["termos_positivos"] = positive_hits
    if negative_hits:
        result["termos_negativos"] = negative_hits

    return result
