# CREA-RS Validation Automation

Automated utilities to request, analyze, and decide on diploma validation replies for CREA-RS.

## Modules
- `validation_automation/email_sender.py`: builds and sends validation requests using SMTP credentials stored in environment variables.
- `validation_automation/email_receiver_analyzer.py`: simulates mailbox polling and applies NLP heuristics to institutional replies.
- `validation_automation/decision_maker.py`: applies CREA-RS thresholds and decides whether to auto-approve or route to manual review.
- `example_usage.py`: minimal orchestration example that demonstrates analysis and decision flow.

### Novo projeto robusto
O diretório `Review CREA Connect AI project/` contém uma versão mais robusta e completa do fluxo, incluindo modelos de dados, templates, analisador, regras de decisão e exemplo ponta a ponta.

Inclui também um CLI de portal interativo (`examples/cli_portal.py`) que serve tanto para o solicitante registrar seus dados quanto para a equipe CREA ingerir respostas e aplicar revisão manual quando o score não atingir o necessário.
Há ainda um comando de exportação que gera um pacote ZIP com os detalhes da submissão para download ou auditoria offline.

## SMTP configuration
Define the following variables before sending emails:
```
CREA_SMTP_HOST
CREA_SMTP_PORT
CREA_SMTP_USER
CREA_SMTP_PASSWORD
CREA_SMTP_SENDER  # optional override for the From header
```

### Execução rápida no Windows
Use o script `run_crea_portal.bat` na raiz do repositório para encaminhar qualquer comando para o CLI do portal sem se preocupar com o caminho do projeto:

```
run_crea_portal.bat list
run_crea_portal.bat applicant-submit "Nome Exemplo" 123.456.789-00 MAT123 Engenharia 3600 "2018/01-2022/12" 01/02/2023 "Instituição X" contato@exemplo.com --dry-run
```
O BAT troca para o diretório `Review CREA Connect AI project/` e executa `python -m review_crea_connect_ai.examples.cli_portal` com todos os argumentos repassados.
