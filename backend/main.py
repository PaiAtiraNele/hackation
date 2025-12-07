import hashlib
import time
from datetime import datetime
from typing import Optional, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

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
    email = Column(String)
    endereco = Column(String)
    situacao_militar = Column(String)
    tipo_validacao = Column(String)  # 'QRCODE' ou 'PDF'
    instituicao = Column(String)
    curso = Column(String)
    status = Column(String, default="EM_ANALISE")
    score_ia = Column(Integer)
    hash_blockchain = Column(String, nullable=True)
    assinatura_status = Column(String, default="PENDENTE")
    assinatura_hash = Column(String, nullable=True)
    assinatura_preview = Column(String, nullable=True)
    etapas = Column(JSON, default=dict)
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


# Utilitários

def registrar_etapa(solicitacao: Solicitacao, etapa: str, status: str, detalhe: Optional[str] = None):
    etapas: Dict[str, Dict[str, str]] = solicitacao.etapas or {}
    etapas[etapa] = {
        "status": status,
        "detalhe": detalhe or "",
        "timestamp": datetime.utcnow().isoformat(),
    }
    solicitacao.etapas = etapas


# Modelos
class QRCodeRequest(BaseModel):
    qr_content: str
    user_cpf: str
    solicitacao_id: Optional[int] = None


class IniciarProcessoRequest(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    endereco: str
    situacao_militar: str


# Rotas
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
            "nivel": "OURO"
        }
    }


@app.post("/processo/iniciar")
def iniciar_processo(req: IniciarProcessoRequest, db: Session = Depends(get_db)):
    """Cria um processo salvo de forma incremental."""
    nova_sol = Solicitacao(
        nome=req.nome,
        cpf=req.cpf,
        email=req.email,
        endereco=req.endereco,
        situacao_militar=req.situacao_militar,
        status="DADOS_IMPORTADOS",
        score_ia=0,
    )
    registrar_etapa(nova_sol, "dados", "VALIDADO", "Dados importados via Gov.br e e-mail verificado")
    db.add(nova_sol)
    db.commit()
    db.refresh(nova_sol)
    return {
        "id": nova_sol.id,
        "status": nova_sol.status,
        "etapas": nova_sol.etapas,
    }


@app.post("/validar/qrcode")
def validar_qrcode(req: QRCodeRequest, db: Session = Depends(get_db)):
    time.sleep(1.5)
    if "edu" in req.qr_content or "mec" in req.qr_content or "ufrgs" in req.qr_content:
        score = 100
        msg = "Autenticidade digital confirmada na fonte."
        valid = True
    else:
        score = 20
        msg = "QR Code não reconhecido. Documentação encaminhada para revisão manual."
        valid = False

    instituicao = "Identificada via URL" if valid else "Desconhecida"

    if req.solicitacao_id:
        solicitacao = db.query(Solicitacao).filter(Solicitacao.id == req.solicitacao_id).first()
        if solicitacao:
            solicitacao.tipo_validacao = "QRCODE"
            solicitacao.score_ia = score
            solicitacao.status = "VALIDADO_QR" if valid else "REVISÃO_HUMANA"
            registrar_etapa(solicitacao, "documentos", solicitacao.status, msg)
            db.commit()

    return {
        "valid": valid,
        "score": score,
        "instituicao": instituicao,
        "msg": msg,
        "human_review": not valid
    }


@app.post("/upload/analisar")
async def analisar_documento(
    file: UploadFile = File(...),
    nome: str = Form(...),
    cpf: str = Form(...),
    endereco: str = Form(...),
    militar: str = Form(...),
    solicitacao_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    time.sleep(2.0)
    filename = file.filename.lower()

    if "erro" in filename or "fake" in filename:
        score = 35
        inst = "Desconhecida"
        curso = "N/A"
        status = "REVISÃO_HUMANA"
        detalhe = "Documento fora do padrão esperado."
    else:
        score = 98
        inst = "UFRGS"
        curso = "Engenharia Civil"
        status = "APROVADO_IA"
        detalhe = "Estrutura do diploma dentro do padrão MEC/INEP."

    nova_sol: Optional[Solicitacao] = None
    if solicitacao_id:
        nova_sol = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()

    if not nova_sol:
        nova_sol = Solicitacao(
            nome=nome,
            cpf=cpf,
            endereco=endereco,
            situacao_militar=militar,
            tipo_validacao="PDF",
            instituicao=inst,
            curso=curso,
            status=status,
            score_ia=score,
        )
        registrar_etapa(nova_sol, "dados", "VALIDADO", "Dados importados via Gov.br")
    else:
        nova_sol.tipo_validacao = "PDF"
        nova_sol.instituicao = inst
        nova_sol.curso = curso
        nova_sol.status = status
        nova_sol.score_ia = score

    registrar_etapa(nova_sol, "documentos", status, detalhe)
    db.add(nova_sol)
    db.commit()
    db.refresh(nova_sol)

    return {
        "id": nova_sol.id,
        "score": score,
        "analise": {
            "instituicao": inst,
            "curso": curso,
            "ocr_confidence": "0.98",
            "detalhe": detalhe,
        },
        "human_review": status == "REVISÃO_HUMANA"
    }


@app.post("/assinatura/processar")
async def processar_assinatura(
    file: UploadFile = File(...),
    solicitacao_id: int = Form(...),
    db: Session = Depends(get_db)
):
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    content = await file.read()
    if not file.content_type.startswith("image"):
        raise HTTPException(status_code=400, detail="Envie uma imagem escaneada da assinatura")

    hash_code = hashlib.sha256(content).hexdigest()
    status = "ASSINATURA_OK"
    detalhe = "Assinatura recortada na área delimitada para impressão."

    filename = file.filename.lower()
    if "borrada" in filename or "clara" in filename:
        status = "REVISÃO_HUMANA"
        detalhe = "Assinatura ilegível. Requer validação manual do CREA."

    preview_url = f"https://dummyimage.com/320x120/000/fff.png&text=Recorte+{hash_code[:6]}"

    solicitacao.assinatura_status = status
    solicitacao.assinatura_hash = hash_code
    solicitacao.assinatura_preview = preview_url
    registrar_etapa(solicitacao, "assinatura", status, detalhe)
    solicitacao.status = status if status != "REVISÃO_HUMANA" else "REVISÃO_HUMANA"
    db.commit()

    return {
        "assinatura_status": status,
        "assinatura_hash": hash_code,
        "preview": preview_url,
        "human_review": status == "REVISÃO_HUMANA",
        "detalhe": detalhe,
    }


@app.post("/blockchain/registrar/{solicitacao_id}")
def registrar_blockchain(solicitacao_id: int, db: Session = Depends(get_db)):
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Not Found")

    raw = f"{solicitacao.cpf}{solicitacao.curso}{datetime.utcnow()}"
    hash_code = hashlib.sha256(raw.encode()).hexdigest()

    solicitacao.hash_blockchain = "0x" + hash_code
    solicitacao.status = "REGISTRADO_BLOCKCHAIN"
    registrar_etapa(solicitacao, "blockchain", "REGISTRADO", "Hash gravado em rede privada")
    db.commit()

    return {"hash": solicitacao.hash_blockchain, "etapas": solicitacao.etapas}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
