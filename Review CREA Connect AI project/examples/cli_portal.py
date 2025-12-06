"""CLI interface for applicants and CREA staff interactions.

Run with ``python -m review_crea_connect_ai.examples.cli_portal``.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from review_crea_connect_ai.data_models import InstitutionData, SolicitationData
from review_crea_connect_ai.interface import (
    PortalState,
    ValidationPortal,
    export_submission_zip,
    pending_manual_reviews,
)


DEFAULT_STATE_PATH = Path("portal_state.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portal interativo CREA Connect AI")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("applicant-submit", help="Registrar solicitação de validação")
    submit.add_argument("nome", help="Nome completo do solicitante")
    submit.add_argument("cpf", help="CPF do solicitante")
    submit.add_argument("matricula", help="Matrícula interna")
    submit.add_argument("curso", help="Curso/Habilitação")
    submit.add_argument("carga_horaria", help="Carga horária total")
    submit.add_argument("periodo", help="Período de conclusão (ex: 2018/01-2022/12)")
    submit.add_argument("colacao", help="Data de colação/emissão (DD/MM/AAAA)")
    submit.add_argument("instituicao_nome", help="Nome da instituição")
    submit.add_argument("instituicao_email", help="E-mail da instituição")
    submit.add_argument(
        "--dry-run",
        action="store_true",
        help="Não enviar e-mail, apenas registrar e simular envio",
    )

    ingest = sub.add_parser(
        "ingest-response", help="Registrar resposta da instituição e analisar"
    )
    ingest.add_argument("submission_id", help="ID da submissão")
    ingest.add_argument("email_body", help="Texto completo do e-mail de resposta")

    review = sub.add_parser(
        "resolve-manual", help="Registrar decisão manual pelo time CREA"
    )
    review.add_argument("submission_id", help="ID da submissão")
    review.add_argument("parecer", help="Justificativa do avaliador")
    review.add_argument(
        "--aprovar",
        action="store_true",
        help="Indica aprovação manual (padrão: reprovar se ausente)",
    )

    sub.add_parser("list", help="Listar submissões e status principais")

    export_cmd = sub.add_parser(
        "export-package", help="Exportar submissão como arquivo ZIP"
    )
    export_cmd.add_argument("submission_id", help="ID da submissão")
    export_cmd.add_argument(
        "destination",
        help="Caminho do arquivo ZIP a ser gerado (ex: exports/pacote.zip)",
    )
    export_cmd.add_argument(
        "--sem-historico",
        action="store_true",
        help="Não incluir history.txt no pacote",
    )

    return parser.parse_args()


def load_state(path: Path) -> PortalState:
    return PortalState.load(path)


def save_state(path: Path, state: PortalState) -> None:
    state.save(path)


def cmd_submit(args: argparse.Namespace) -> None:
    state = load_state(DEFAULT_STATE_PATH)
    portal = ValidationPortal()
    submission_id = portal.submit_application(
        state,
        SolicitationData(
            nome_completo=args.nome,
            cpf=args.cpf,
            data_nascimento=None,
            matricula=args.matricula,
            curso=args.curso,
            carga_horaria=args.carga_horaria,
            periodo_conclusao=args.periodo,
            data_colacao=args.colacao,
        ),
        InstitutionData(nome=args.instituicao_nome, email_contato=args.instituicao_email),
        send_email=not args.dry_run,
    )
    save_state(DEFAULT_STATE_PATH, state)
    print(f"Submissão registrada com ID: {submission_id}")
    print(f"Status inicial: {state.submissions[submission_id].status}")


def cmd_ingest(args: argparse.Namespace) -> None:
    state = load_state(DEFAULT_STATE_PATH)
    portal = ValidationPortal()
    analysis = portal.ingest_response(state, args.submission_id, args.email_body)
    save_state(DEFAULT_STATE_PATH, state)
    print(f"Análise concluída: status {analysis.status}, score {analysis.score}")
    if analysis.protocolo_encontrado:
        print(f"Protocolo encontrado: {analysis.protocolo_encontrado}")


def cmd_review(args: argparse.Namespace) -> None:
    state = load_state(DEFAULT_STATE_PATH)
    portal = ValidationPortal()
    outcome = portal.resolve_manual_review(
        state,
        args.submission_id,
        aprovado=args.aprovar,
        parecer=args.parecer,
    )
    save_state(DEFAULT_STATE_PATH, state)
    print(f"Decisão manual registrada: {outcome.status}")
    print(outcome.message)


def cmd_list(_: argparse.Namespace) -> None:
    state = load_state(DEFAULT_STATE_PATH)
    print("=== Submissões registradas ===")
    for sid, rec in state.submissions.items():
        print(f"ID: {sid}")
        print(f"  Solicitante: {rec.solicitant.nome_completo}")
        print(f"  Status: {rec.status}")
        if rec.analysis:
            print(
                f"  Score: {rec.analysis.score} | Protocolo: {rec.protocolo or '—'} | Decisão: {rec.decision.status}"
            )
    pending = list(pending_manual_reviews(state))
    if pending:
        print("\nCasos aguardando revisão manual:")
        for sid, _ in pending:
            print(f" - {sid}")


def cmd_export(args: argparse.Namespace) -> None:
    state = load_state(DEFAULT_STATE_PATH)
    destination = Path(args.destination)
    export_submission_zip(
        state,
        args.submission_id,
        destination,
        include_history=not args.sem_historico,
    )
    print(f"Pacote exportado para {destination}")


def main() -> None:
    args = parse_args()
    if args.command == "applicant-submit":
        cmd_submit(args)
    elif args.command == "ingest-response":
        cmd_ingest(args)
    elif args.command == "resolve-manual":
        cmd_review(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "export-package":
        cmd_export(args)


if __name__ == "__main__":
    main()

