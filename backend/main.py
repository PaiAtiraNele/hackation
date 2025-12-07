import hashlib
import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
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
    etapa_dados_status = Column(String, default="PENDENTE")
    etapa_diploma_status = Column(String, default="PENDENTE")
    etapa_assinatura_status = Column(String, default="PENDENTE")
    score_ia = Column(Integer)
    hash_blockchain = Column(String, nullable=True)
    assinatura_url = Column(String, nullable=True)
    precisa_validacao_humana = Column(Boolean, default=False)
    observacao = Column(String, nullable=True)
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


class ProcessoRequest(BaseModel):
    nome: str
    cpf: str
    endereco: str
    situacao_militar: str
    nivel: Optional[str] = None


@app.post("/processo/iniciar")
def iniciar_processo(payload: ProcessoRequest, db: Session = Depends(get_db)):
    """Armazena os dados trazidos do Gov.br e já roda a conferência básica."""

    time.sleep(1.0)
    # Simulação: usuários com nível OURO recebem pontuação maior
    score_dados = 95 if payload.nivel == "OURO" else 75
    precisa_validacao_humana = score_dados < 80

    solicitacao = Solicitacao(
        nome=payload.nome,
        cpf=payload.cpf,
        endereco=payload.endereco,
        situacao_militar=payload.situacao_militar,
        etapa_dados_status="VALIDADO" if not precisa_validacao_humana else "REVISAO",
        status="DADOS_IMPORTADOS",
        score_ia=score_dados,
        observacao=("Dados incompletos, enviar para validação humana." if precisa_validacao_humana else None),
    )
    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    return {
        "id": solicitacao.id,
        "score_dados": score_dados,
        "precisa_validacao_humana": precisa_validacao_humana,
        "status": solicitacao.status,
    }


# Rota 2: Validação via QR Code
class QRCodeRequest(BaseModel):
    qr_content: str
    user_cpf: str
    solicitacao_id: int


@app.post("/validar/qrcode")
def validar_qrcode(req: QRCodeRequest, db: Session = Depends(get_db)):
    time.sleep(1.5)
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == req.solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    # Lógica de Demo: Links com 'edu' ou 'ufrgs' são aprovados
    if "edu" in req.qr_content or "mec" in req.qr_content or "ufrgs" in req.qr_content:
        score = 100
        msg = "Autenticidade digital confirmada na fonte."
        valid = True
    else:
        score = 20
        msg = "QR Code não reconhecido."
        valid = False

    solicitacao.tipo_validacao = "QRCODE"
    solicitacao.instituicao = "Identificada via URL"
    solicitacao.curso = "Engenharia"
    solicitacao.score_ia = max(solicitacao.score_ia or 0, score)
    solicitacao.etapa_diploma_status = "APROVADO" if valid else "RECUSADO"
    solicitacao.precisa_validacao_humana = not valid
    solicitacao.observacao = None if valid else "Requer conferência manual do diploma."
    db.commit()

    return {
        "valid": valid,
        "score": score,
        "instituicao": solicitacao.instituicao,
        "msg": msg,
        "precisa_validacao_humana": solicitacao.precisa_validacao_humana,
    }


# Rota 3: Upload PDF + Dados
@app.post("/upload/analisar")
async def analisar_documento(
    solicitacao_id: int = Form(...),
    file: UploadFile = File(...),
    nome: str = Form(...),
    cpf: str = Form(...),
    endereco: str = Form(...),
    militar: str = Form(...),
    db: Session = Depends(get_db),
):
    time.sleep(2.0)
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    filename = file.filename.lower()

    # Lógica de Demo para Apresentação
    if "erro" in filename:
        score = 35
        inst = "Desconhecida"
        curso = "N/A"
        status_final = "REVISAO"
        observacao = "Pontuação baixa, revisão humana necessária."
        precisa_validacao_humana = True
    else:
        score = 98
        inst = "UFRGS"
        curso = "Engenharia Civil"
        status_final = "APROVADO_IA"
        observacao = None
        precisa_validacao_humana = False

    solicitacao.nome = nome
    solicitacao.cpf = cpf
    solicitacao.endereco = endereco
    solicitacao.situacao_militar = militar
    solicitacao.tipo_validacao = "PDF"
    solicitacao.instituicao = inst
    solicitacao.curso = curso
    solicitacao.score_ia = score
    solicitacao.status = status_final
    solicitacao.etapa_diploma_status = "APROVADO" if score > 80 else "RECUSADO"
    solicitacao.precisa_validacao_humana = precisa_validacao_humana
    solicitacao.observacao = observacao
    db.commit()
    db.refresh(solicitacao)

    return {
        "id": solicitacao.id,
        "score": score,
        "analise": {"instituicao": inst, "curso": curso, "ocr_confidence": "0.98"},
        "precisa_validacao_humana": precisa_validacao_humana,
        "status": solicitacao.status,
    }


class AssinaturaResponse(BaseModel):
    status: str
    observacao: Optional[str]
    precisa_validacao_humana: bool


@app.post("/assinatura/capturar", response_model=AssinaturaResponse)
async def capturar_assinatura(
    solicitacao_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Simula a captura de assinatura manual escaneada com caneta preta."""

    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
        raise HTTPException(status_code=400, detail="Formato de assinatura não suportado")

    # Mock: assinatura com nome "recorte" será considerada com baixa qualidade
    content = await file.read()
    baixa_qualidade = b"recorte" in content.lower()

    solicitacao.assinatura_url = f"assinaturas/{file.filename}"
    solicitacao.etapa_assinatura_status = "PENDENTE_RECORTE" if baixa_qualidade else "CAPTURADA"
    solicitacao.precisa_validacao_humana = baixa_qualidade or solicitacao.precisa_validacao_humana
    solicitacao.observacao = (
        "Recortar área delimitada e reprocessar assinatura."
        if baixa_qualidade
        else "Assinatura pronta para impressão na carteirinha."
    )
    db.commit()

    return AssinaturaResponse(
        status=solicitacao.etapa_assinatura_status,
        observacao=solicitacao.observacao,
        precisa_validacao_humana=solicitacao.precisa_validacao_humana,
    )


# Rota 4: Blockchain
@app.post("/blockchain/registrar/{solicitacao_id}")
def registrar_blockchain(solicitacao_id: int, db: Session = Depends(get_db)):
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Not Found")

    raw = f"{solicitacao.cpf}{solicitacao.curso}{datetime.utcnow()}"
    hash_code = hashlib.sha256(raw.encode()).hexdigest()

    solicitacao.hash_blockchain = "0x" + hash_code
    solicitacao.status = (
        "VALIDACAO_MANUAL_REQUERIDA"
        if solicitacao.precisa_validacao_humana
        else "REGISTRADO_BLOCKCHAIN"
    )
    db.commit()

    return {
        "hash": solicitacao.hash_blockchain,
        "status": solicitacao.status,
        "precisa_validacao_humana": solicitacao.precisa_validacao_humana,
        "observacao": solicitacao.observacao,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
