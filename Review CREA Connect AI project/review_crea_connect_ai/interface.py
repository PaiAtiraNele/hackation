"""Interactive-facing helpers for applicants and CREA staff workflows.

This module offers a minimal state container plus portal-style helpers to:
- let applicants submit validation requests (optionally sending real SMTP mail)
- ingest institutional responses and run automated analysis/decisioning
- expose a manual review path when confidence is below threshold
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from .data_models import InstitutionData, SolicitationData
from .decision import DecisionOutcome, InMemoryNotifier, process_validation_result
from .email_sender import EmailDeliveryError, send_validation_email
from .response_analyzer import ResponseAnalysis, analyze_response_content


@dataclass
class SubmissionRecord:
    """Represents a single applicant submission and its lifecycle."""

    solicitant: SolicitationData
    institution: InstitutionData
    message_id: str
    status: str = "AGUARDANDO_RESPOSTA"
    analysis: ResponseAnalysis | None = None
    decision: DecisionOutcome | None = None
    protocolo: str | None = None
    history: list[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        data = asdict(self)
        data["solicitant"]["data_nascimento"] = (
            self.solicitant.data_nascimento.isoformat()
            if self.solicitant.data_nascimento
            else None
        )
        return data


@dataclass
class PortalState:
    """Persistable state for applicant and staff interactions."""

    submissions: Dict[str, SubmissionRecord] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        snapshot = {sid: rec.to_json() for sid, rec in self.submissions.items()}
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "PortalState":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        submissions: Dict[str, SubmissionRecord] = {}
        for sid, payload in raw.items():
            solicitant = SolicitationData(
                nome_completo=payload["solicitant"]["nome_completo"],
                cpf=payload["solicitant"]["cpf"],
                data_nascimento=None,
                matricula=payload["solicitant"]["matricula"],
                curso=payload["solicitant"]["curso"],
                carga_horaria=payload["solicitant"]["carga_horaria"],
                periodo_conclusao=payload["solicitant"]["periodo_conclusao"],
                data_colacao=payload["solicitant"]["data_colacao"],
            )
            institution = InstitutionData(
                nome=payload["institution"]["nome"],
                email_contato=payload["institution"]["email_contato"],
            )
            analysis_payload = payload.get("analysis")
            analysis = None
            if analysis_payload:
                analysis = ResponseAnalysis(**analysis_payload)
            decision_payload = payload.get("decision")
            decision = None
            if decision_payload:
                decision = DecisionOutcome(**decision_payload)
            submissions[sid] = SubmissionRecord(
                solicitant=solicitant,
                institution=institution,
                message_id=payload.get("message_id", ""),
                status=payload.get("status", "AGUARDANDO_RESPOSTA"),
                analysis=analysis,
                decision=decision,
                protocolo=payload.get("protocolo"),
                history=list(payload.get("history", [])),
            )
        return cls(submissions=submissions)


class ValidationPortal:
    """Coordinates applicant submissions and staff review flows."""

    def __init__(
        self,
        *,
        notifier: InMemoryNotifier | None = None,
        send_callable: Callable[[SolicitationData, InstitutionData], str] | None = None,
        analyzer: Callable[[str], ResponseAnalysis] = analyze_response_content,
    ) -> None:
        self.notifier = notifier or InMemoryNotifier()
        self.send_callable = send_callable or (
            lambda s, i: send_validation_email(s, i)
        )
        self.analyzer = analyzer

    def submit_application(
        self,
        state: PortalState,
        solicitant: SolicitationData,
        institution: InstitutionData,
        *,
        send_email: bool = True,
    ) -> str:
        """Register a new application and optionally send the validation email."""

        submission_id = uuid.uuid4().hex[:12]
        history = ["Submissão registrada pelo solicitante"]

        if send_email:
            try:
                msg_id = self.send_callable(solicitant, institution)
                history.append("E-mail de validação enviado à instituição")
            except EmailDeliveryError as exc:  # pragma: no cover - network dependent
                history.append(f"Falha ao enviar e-mail: {exc}")
                msg_id = "ERRO"
        else:
            msg_id = "SIMULADO"
            history.append("Envio de e-mail simulado (modo dry-run)")

        state.submissions[submission_id] = SubmissionRecord(
            solicitant=solicitant,
            institution=institution,
            message_id=msg_id,
            history=history,
        )
        return submission_id

    def ingest_response(
        self, state: PortalState, submission_id: str, email_body: str
    ) -> ResponseAnalysis:
        """Process the institutional response and update records."""

        if submission_id not in state.submissions:
            raise KeyError(f"ID de submissão desconhecido: {submission_id}")

        record = state.submissions[submission_id]
        analysis = self.analyzer(email_body)
        decision = process_validation_result(
            analysis,
            submission_id,
            record.solicitant.nome_completo,
            notifier=self.notifier,
        )

        record.status = analysis.status
        record.analysis = analysis
        record.decision = decision
        record.protocolo = analysis.protocolo_encontrado
        record.history.append("Resposta institucional analisada")
        if decision.status == "REVISAO_MANUAL":
            record.history.append("Encaminhado para revisão manual")
        else:
            record.history.append("Validação confirmada automaticamente")

        return analysis

    def resolve_manual_review(
        self,
        state: PortalState,
        submission_id: str,
        *,
        aprovado: bool,
        parecer: str,
    ) -> DecisionOutcome:
        """Staff resolution for cases routed to manual review."""

        if submission_id not in state.submissions:
            raise KeyError(f"ID de submissão desconhecido: {submission_id}")

        record = state.submissions[submission_id]
        status = "APROVADO_MANUAL" if aprovado else "REPROVADO_MANUAL"
        message = f"Revisão manual concluída: {parecer}"

        record.status = status
        record.history.append(message)
        outcome = DecisionOutcome(status=status, message=message)
        record.decision = outcome
        return outcome


def pending_manual_reviews(state: PortalState) -> Iterable[tuple[str, SubmissionRecord]]:
    """Helper to list submissions awaiting manual review."""

    return (
        (sid, rec)
        for sid, rec in state.submissions.items()
        if rec.decision and rec.decision.status == "REVISAO_MANUAL"
    )


def export_submission_zip(
    state: PortalState,
    submission_id: str,
    destination: Path,
    *,
    include_history: bool = True,
) -> Path:
    """Exporta um pacote ZIP com os dados de uma submissão.

    O pacote inclui `submission.json` com todos os campos serializados e, opcionalmente,
    um `history.txt` com o histórico de eventos. Facilita o compartilhamento ou download
    de um dossiê para revisão offline.
    """

    if submission_id not in state.submissions:
        raise KeyError(f"ID de submissão desconhecido: {submission_id}")

    record = state.submissions[submission_id]
    payload = record.to_json()
    payload["submission_id"] = submission_id

    destination.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(destination, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("submission.json", json.dumps(payload, ensure_ascii=False, indent=2))
        if include_history:
            history_text = "\n".join(record.history) if record.history else "(sem histórico)"
            zf.writestr("history.txt", history_text)

    return destination

