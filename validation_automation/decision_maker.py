"""Business logic for handling validation analysis results."""
from typing import Dict

THRESHOLD_CONFIRMATION = 0.85


def process_validation_result(analysis_result: Dict[str, object], solicitant_id: str, *, solicitant_name: str = "") -> Dict[str, object]:
    """Process the analysis result and decide next actions.

    Args:
        analysis_result: Output from ``analyze_response_content``.
        solicitant_id: Identifier for the solicitation in the CREA-RS system.
        solicitant_name: Optional human-readable name for notifications.

    Returns:
        A dictionary describing the action taken, useful for downstream orchestration
        and logging.
    """

    actions: Dict[str, object] = {
        "solicitant_id": solicitant_id,
        "status": analysis_result.get("status"),
        "score": analysis_result.get("score"),
    }

    if analysis_result.get("score", 0) >= THRESHOLD_CONFIRMATION:
        actions.update(
            {
                "registro_criado": True,
                "notificacao_solicitante": "Validação da Instituição Recebida e Confirmada.",
            }
        )
    else:
        motivo = analysis_result.get("motivo", "Termos negativos ou ambíguos")
        nome_destino = solicitant_name or "solicitante"
        actions.update(
            {
                "registro_criado": False,
                "alerta_revisao": {
                    "mensagem": "Validação requer análise manual.",
                    "motivo": motivo,
                },
                "notificacao_interna": f"Atenção: Validação de {nome_destino} requer análise manual. Score: {analysis_result.get('score', 0):.2f}.",
            }
        )

    if analysis_result.get("protocolo_encontrado"):
        actions["protocolo"] = analysis_result["protocolo_encontrado"]

    return actions
