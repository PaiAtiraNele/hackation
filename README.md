# CREA Connect AI

Protótipo MVP (V2.0) desenvolvido para o Hackathon CREA-RS 2025. O objetivo é otimizar o registro profissional (Pessoa Física) automatizando a coleta de dados via Gov.br, a validação de diplomas por QR Code ou OCR em PDF e o registro da aprovação em blockchain.

## Estrutura
- **backend/**: API em FastAPI simulando integrações com Gov.br, análise de diplomas e registro em blockchain.
- **frontend/**: Single Page App (Vue 3 + Tailwind via CDN) que orquestra o fluxo de login, revisão de dados, validação acadêmica e confirmação final.

## Executando o backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Executando o frontend
Abra `frontend/index.html` no navegador e garanta que o backend esteja rodando em `http://127.0.0.1:8000`.
