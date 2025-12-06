# Review CREA Connect AI project

Toolkit aprimorado para automatizar o fluxo de validação de diplomas do CREA-RS: envio do e-mail oficial, análise da resposta com heurísticas de NLP e decisão automática ou direcionamento para revisão humana.

## Componentes
- `review_crea_connect_ai/config.py`: carrega configuração SMTP a partir de variáveis de ambiente e define o limiar global de confiança.
- `review_crea_connect_ai/data_models.py`: modelos de dados para solicitante e instituição.
- `review_crea_connect_ai/email_templates.py`: assunto e corpo do e-mail oficial.
- `review_crea_connect_ai/email_sender.py`: envio seguro via SMTP com controle de timeout e mensagens de erro específicas.
- `review_crea_connect_ai/response_analyzer.py`: análise da resposta, extração de protocolo e cálculo de score.
- `review_crea_connect_ai/decision.py`: regras de negócio do CREA-RS para aprovação automática ou alerta.
- `review_crea_connect_ai/interface.py`: estado persistente e fluxo portal (solicitante + equipe CREA).
- `review_crea_connect_ai/mailbox.py`: utilitário simples para processar múltiplas respostas obtidas de uma caixa postal.
- `examples/sample_workflow.py`: demonstração ponta a ponta em modo offline.
- `examples/cli_portal.py`: CLI interativa para submissão do solicitante, ingestão de respostas e revisão manual.

## Configuração SMTP
Defina as variáveis de ambiente antes de enviar e-mails reais:

```
CREA_SMTP_HOST
CREA_SMTP_PORT  # padrão 587
CREA_SMTP_USER
CREA_SMTP_PASSWORD
CREA_SMTP_SENDER  # opcional; usa o usuário por padrão
```

## Uso rápido
```bash
python "Review CREA Connect AI project/examples/sample_workflow.py"
```
A execução imprime a análise simulada, a decisão e as notificações registradas.

### Interface de interação (solicitante + equipe CREA)
```bash
cd "Review CREA Connect AI project"
# Solicitante envia dados e, opcionalmente, dispara o e-mail oficial (use --dry-run para simular)
python -m review_crea_connect_ai.examples.cli_portal applicant-submit "Nome Exemplo" 123.456.789-00 MAT123 Engenharia 3600 "2018/01-2022/12" 01/02/2023 "Instituição X" contato@exemplo.com --dry-run

# CREA importa a resposta recebida e gera decisão automática
python -m review_crea_connect_ai.examples.cli_portal ingest-response <ID_GERADO> "Confirmamos os dados. Protocolo: ABCD-1234"

# Lista geral (mostra fila de revisão manual, se houver)
python -m review_crea_connect_ai.examples.cli_portal list

# Exporta um pacote ZIP com os dados e histórico da submissão
python -m review_crea_connect_ai.examples.cli_portal export-package <ID_GERADO> exports/pacote.zip
python -m review_crea_connect_ai.examples.cli_portal export-package <ID_GERADO> exports/pacote_sem_historico.zip --sem-historico

# Caso o score fique abaixo do limiar, a equipe registra o parecer manual
python -m review_crea_connect_ai.examples.cli_portal resolve-manual <ID_GERADO> "Documento legível, aprovado" --aprovar
```
O arquivo `portal_state.json` mantém o histórico entre execuções, permitindo uma interface simples para solicitantes e analistas.

### Atalho Windows (BAT)
No Windows, basta executar na raiz do repositório:

```
run_crea_portal.bat list
```

Qualquer argumento passado é encaminhado ao módulo `review_crea_connect_ai.examples.cli_portal` após o BAT alterar o diretório para `Review CREA Connect AI project/`.

## Pontos de robustez incluídos
- Sanitização de CPF no assunto para evitar caracteres inesperados.
- Timeout configurável em operações SMTP.
- Tratamento de erros de envio com exceção específica `EmailDeliveryError`.
- Score de confiança com termos positivos/negativos e bônus por protocolo.
- Exportação em ZIP do dossiê (JSON + histórico) para baixar ou enviar a revisores.
- Objeto `InMemoryNotifier` para inspeção fácil das notificações geradas.
