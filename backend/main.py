import hashlib
import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Configuração DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./crea_hackathon_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Modelo de Dados
class Solicitacao(Base):
    __tablename__ = "solicitacoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    cpf = Column(String)
    endereco = Column(String)
    situacao_militar = Column(String)
    tipo_validacao = Column(String)  # 'QRCODE' ou 'PDF'
    instituicao = Column(String)
    curso = Column(String)
    status = Column(String, default="EM_ANALISE")
    score_ia = Column(Integer)
    hash_blockchain = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="CREA Connect AI - V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Rota 1: Login Simulado (Gov.br)
@app.post("/auth/govbr")
def login_govbr():
    time.sleep(1.0)
    return {
        "access_token": "govbr_token_v2",
        "user": {
            "nome": "João da Silva Engenheiro",
            "cpf": "***.456.789-**",
            "rg": "10********",
            "foto": "https://i.pravatar.cc/300?img=11",
            "endereco": "Av. Ipiranga, 6681 - Porto Alegre/RS",
            "situacao_militar": "Dispensado (Certificado de Reservista)",
            "nivel": "OURO",
        },
    }


# Rota 2: Validação via QR Code
class QRCodeRequest(BaseModel):
    qr_content: str
    user_cpf: str


@app.post("/validar/qrcode")
def validar_qrcode(req: QRCodeRequest, db: Session = Depends(get_db)):
    time.sleep(1.5)
    # Lógica de Demo: Links com 'edu' ou 'ufrgs' são aprovados
    if "edu" in req.qr_content or "mec" in req.qr_content or "ufrgs" in req.qr_content:
        score = 100
        msg = "Autenticidade digital confirmada na fonte."
    else:
        score = 20
        msg = "QR Code não reconhecido."

    return {
        "valid": score > 50,
        "score": score,
        "instituicao": "Identificada via URL",
        "msg": msg,
    }


# Rota 3: Upload PDF + Dados
@app.post("/upload/analisar")
async def analisar_documento(
    file: UploadFile = File(...),
    nome: str = Form(...),
    cpf: str = Form(...),
    endereco: str = Form(...),
    militar: str = Form(...),
    db: Session = Depends(get_db),
):
    time.sleep(2.0)
    filename = file.filename.lower()

    # Lógica de Demo para Apresentação
    if "erro" in filename:
        score = 35
        inst = "Desconhecida"
        curso = "N/A"
    else:
        score = 98
        inst = "UFRGS"
        curso = "Engenharia Civil"

    nova_sol = Solicitacao(
        nome=nome,
        cpf=cpf,
        endereco=endereco,
        situacao_militar=militar,
        tipo_validacao="PDF",
        instituicao=inst,
        curso=curso,
        status="APROVADO_IA" if score > 80 else "REVISAO",
        score_ia=score,
    )
    db.add(nova_sol)
    db.commit()
    db.refresh(nova_sol)

    return {
        "id": nova_sol.id,
        "score": score,
        "analise": {"instituicao": inst, "curso": curso, "ocr_confidence": "0.98"},
    }


# Rota 4: Blockchain
@app.post("/blockchain/registrar/{solicitacao_id}")
def registrar_blockchain(solicitacao_id: int, db: Session = Depends(get_db)):
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Not Found")

    raw = f"{solicitacao.cpf}{solicitacao.curso}{datetime.utcnow()}"
    hash_code = hashlib.sha256(raw.encode()).hexdigest()

    solicitacao.hash_blockchain = "0x" + hash_code
    solicitacao.status = "REGISTRADO_BLOCKCHAIN"
    db.commit()

    return {"hash": solicitacao.hash_blockchain}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
