import csv
import hashlib
import random
import time
from datetime import datetime
from io import StringIO
from typing import Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from external_validation import (
    THRESHOLD_CONFIRMATION,
    analyze_response_content,
    check_mailbox_for_response,
    process_validation_result,
    send_validation_email,
)

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
    tipo_validacao = Column(String) # 'QRCODE' ou 'PDF'
    instituicao = Column(String)
    curso = Column(String)
    status = Column(String, default="EM_ANALISE")
    score_ia = Column(Integer)
    hash_blockchain = Column(String, nullable=True)
    etapas = Column(JSON, default=list)
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
    try: yield db
    finally: db.close()

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
            "nivel": "OURO"
        }
    }

# Rota 2: Validação via QR Code
class QRCodeRequest(BaseModel):
    qr_content: str
    user_cpf: str


class EmailStartRequest(BaseModel):
    cpf: str
    email: str


class EmailVerifyRequest(BaseModel):
    cpf: str
    code: str


class DocumentoChecklist(BaseModel):
    doc_type: str


class GovDocValidationRequest(BaseModel):
    cpf: str
    nome: str
    documentos: List[str]
    forcar_falha: bool = False


class OCRValidationRequest(BaseModel):
    cpf: str
    nome: str
    documentos: List[str]
    simular_inconsistencia: bool = False


class SalvarEtapaRequest(BaseModel):
    cpf: str
    solicitacao_id: Optional[int] = None
    etapa: str
    status: str
    detalhes: Optional[Dict] = None


class CursoExternoRequest(BaseModel):
    cpf: str
    nome: str
    curso: str
    instituicao: str
    estado: str
    possui_codigo: bool = False
    contato_instituicao: Optional[str] = None


class ExternalEmailRequest(BaseModel):
    cpf: str
    nome: str
    data_nascimento: str
    matricula: str
    curso: str
    carga_horaria: str
    periodo_conclusao: str
    data_colacao: str
    instituicao: str
    email_instituicao: str
    solicitacao_id: Optional[int] = None


class AvaliarRespostaRequest(BaseModel):
    cpf: str
    resposta: str
    solicitante_id: Optional[int] = None
    solicitante_nome: Optional[str] = None


class CertificadoEspecializacao(BaseModel):
    solicitante: str
    cpf: str
    certificado: str
    instituicao: str
    contato: str
    doc_id: Optional[str] = None
    indicios: Optional[str] = None


class CertificadosBatch(BaseModel):
    certificados: List[CertificadoEspecializacao]

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
        "msg": msg
    }


# Store OTP codes in-memory for demo
_email_codes = {}
_etapas_cache: Dict[str, Dict] = {}


def _registrar_etapa(cpf: str, etapa: str, status: str, detalhes: Optional[Dict] = None):
    cache = _etapas_cache.setdefault(cpf, {})
    cache[etapa] = {
        "status": status,
        "detalhes": detalhes or {},
        "registrado_em": datetime.utcnow().isoformat(),
    }
    return cache[etapa]


def _pontuar_certificado(cert: CertificadoEspecializacao) -> Dict:
    base_score = 93
    if cert.indicios:
        base_score -= 12
    if any(flag in cert.certificado.lower() for flag in ["rascunho", "incompleto", "copia"]):
        base_score -= 10
    if not cert.contato:
        base_score -= 6

    score = max(35, min(99, base_score))
    status = "aprovado" if score >= 90 else "revisao_humana"
    alerta = None if status == "aprovado" else "Pontuação abaixo de 90%. Solicitar conferência manual."

    planilha_row = {
        "Solicitante": cert.solicitante,
        "CPF": cert.cpf,
        "Certificado": cert.certificado,
        "Instituicao": cert.instituicao,
        "Contato": cert.contato or "não informado",
        "DocID": cert.doc_id or "N/D",
        "Score": score,
        "Status": status,
    }

    return {
        "certificado": cert.dict(),
        "score": score,
        "status": status,
        "alerta": alerta,
        "proxima_acao": "Registrar atribuição" if status == "aprovado" else "Acionar instituição via e-mail/telefone",
        "planilha_row": planilha_row,
    }


@app.post("/auth/email/start")
def iniciar_email(req: EmailStartRequest):
    """Simula envio de código de validação via e-mail para CPF informado."""
    code = "".join(str(random.randint(0, 9)) for _ in range(6))
    _email_codes[req.cpf] = {"code": code, "email": req.email, "ts": datetime.utcnow().isoformat()}
    return {
        "sent": True,
        "destino": req.email,
        "code_preview": code if req.email.endswith("@teste.com") else "***",
        "msg": "Código enviado. Verifique seu e-mail."
    }


@app.post("/auth/email/verify")
def verificar_email(req: EmailVerifyRequest):
    registro = _email_codes.get(req.cpf)
    if not registro:
        raise HTTPException(status_code=400, detail="Solicitação de código não encontrada")
    if registro["code"] != req.code:
        raise HTTPException(status_code=401, detail="Código inválido")
    _registrar_etapa(req.cpf, "otp_email", "verificado", {"email": registro["email"]})
    return {"verified": True, "msg": "E-mail verificado com sucesso."}


@app.post("/validar/gov_documentos")
def validar_gov_documentos(req: GovDocValidationRequest):
    """Cruza dados captados do Gov.br com a checagem básica de documentos enviados."""
    time.sleep(1.0)

    documentos_normalizados = [doc.strip() for doc in req.documentos if doc.strip()]
    sinais_alerta = [doc for doc in documentos_normalizados if any(flag in doc.lower() for flag in ["fake", "rascunho", "faltando"])]
    quantidade_ok = len(documentos_normalizados) >= 4
    falha_forcada = req.forcar_falha

    score = 95
    score -= max(0, 4 - len(documentos_normalizados)) * 8
    if sinais_alerta:
        score -= 30
    if falha_forcada:
        score = 42
    score = max(10, min(100, score))

    if score >= 90:
        classificacao = "aprovado_auto"
        status = "conferido"
        mensagem = "Dados conciliados com sucesso (mock)."
        demonstrativo = "Fluxo aprovado automaticamente: documentos suficientes e consistentes."
        proxima_acao = "Prosseguir para diplomas/assinatura sem intervenção humana."
    elif score >= 60:
        classificacao = "revisao_humana"
        status = "pendente_validacao_humana"
        mensagem = "Score abaixo de 90%. Encaminhar para conferência humana."
        demonstrativo = "Demonstração de revisão: documentos incompletos ou suspeitos exigem triagem manual."
        proxima_acao = "Abrir chamado para equipe CREA revisar antes de prosseguir."
    else:
        classificacao = "falha"
        status = "pendente_validacao_humana"
        mensagem = "Inconsistências severas: bloquear avanço e solicitar correção."
        demonstrativo = "Demonstração de falha: dados divergentes e alertas de fraude."
        proxima_acao = "Solicitar reenvio imediato ao solicitante e registrar para auditoria."

    detalhes = {
        "documentos_recebidos": documentos_normalizados,
        "sinais_alerta": sinais_alerta,
        "quantidade_ok": quantidade_ok,
        "mensagem": mensagem,
        "demonstrativo": demonstrativo,
        "score": score,
        "classificacao": classificacao,
        "proxima_acao": proxima_acao,
    }

    _registrar_etapa(req.cpf, "gov_doc", status, detalhes)
    return {"status": status, **detalhes}


@app.post("/ocr/validar")
def validar_ocr(req: OCRValidationRequest):
    """Mock de OCR/IA: analisa estrutura documental e retorna score de veracidade."""
    time.sleep(1.0)

    documentos_normalizados = [doc.strip() for doc in req.documentos if doc.strip()]
    faltantes = [item for item in ["Diploma", "Histórico", "RG", "CPF", "Foto", "Reservista", "PIS", "Tipo sanguíneo"] if not any(item.lower() in d.lower() for d in documentos_normalizados)]

    score = 94
    score -= len(faltantes) * 6
    if req.simular_inconsistencia or any("incons" in d.lower() for d in documentos_normalizados):
        score = min(score, 72)
    score = max(10, min(100, score))

    status = "aprovado" if score >= 90 else "revisao_humana"
    mensagem = "Score >= 90: veracidade confirmada automaticamente." if status == "aprovado" else "Score abaixo de 90: encaminhar para conferência humana." \
        if score >= 60 else "Divergências severas: solicitar correção imediata."

    export_apolo = f"https://apolo.crea-rs.gov.br/export/{req.cpf}"
    export_sic = f"https://sic.crea-rs.gov.br/export/{req.cpf}"
    export_emec = f"https://emec.mec.gov.br/consultar/{req.cpf}"

    resultado = {
        "cpf": req.cpf,
        "nome": req.nome,
        "score": score,
        "status": status,
        "faltantes": faltantes,
        "mensagem": mensagem,
        "proxima_acao": "Liberar para próxima etapa" if status == "aprovado" else "Direcionar para analista CREA",
        "exports": {
            "APOLO": {"url": export_apolo, "status": "pronto"},
            "SIC": {"url": export_sic, "status": "pronto"},
            "EMEC": {"url": export_emec, "status": "consulta"},
        },
    }

    _registrar_etapa(req.cpf, "ocr", status, resultado)
    return resultado

# Rota 3: Upload PDF + Dados
@app.post("/upload/analisar")
async def analisar_documento(
    file: UploadFile = File(...), 
    nome: str = Form(...), 
    cpf: str = Form(...),
    endereco: str = Form(...),
    militar: str = Form(...),
    db: Session = Depends(get_db)
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
        nome=nome, cpf=cpf, endereco=endereco, situacao_militar=militar,
        tipo_validacao="PDF", instituicao=inst, curso=curso,
        status="APROVADO_IA" if score > 80 else "REVISAO",
        score_ia=score,
        etapas=[_etapas_cache.get(cpf, {}), {"documento_pdf": {"status": "analisado", "score": score}}],
    )
    db.add(nova_sol)
    db.commit()
    db.refresh(nova_sol)

    return {
        "id": nova_sol.id,
        "score": score,
        "analise": {"instituicao": inst, "curso": curso, "ocr_confidence": "0.98"}
    }


@app.post("/documentos/analise")
async def analisar_documentos(
    file: UploadFile = File(...),
    doc_type: str = Form("pacote")
):
    """Valida lote de documentos (RG, CPF, reservista, fotos) e estrutura padrão."""
    conteudo = await file.read()
    tamanho_kb = round(len(conteudo) / 1024, 1)
    filename = (file.filename or "").lower()

    estrutura_valida = not any(flag in filename for flag in ["rascunho", "incompleto", "faltando"])
    alerta = None if estrutura_valida else "Estrutura divergente do padrão oficial. Solicitar reenvio ao solicitante."

    if tamanho_kb < 20:
        alerta = "Documento muito pequeno. Envie imagem completa ou PDF agrupado."

    doc_ia_score = 92 if estrutura_valida else 45

    return {
        "doc_type": doc_type,
        "tam_kb": tamanho_kb,
        "estrutura_valida": estrutura_valida,
        "score": doc_ia_score,
        "alerta": alerta,
        "padrao_detectado": "layout_crea_base_v2" if estrutura_valida else "desconhecido",
    }

# Rota 4: Blockchain
@app.post("/blockchain/registrar/{solicitacao_id}")
def registrar_blockchain(solicitacao_id: int, db: Session = Depends(get_db)):
    solicitacao = db.query(Solicitacao).filter(Solicitacao.id == solicitacao_id).first()
    if not solicitacao: raise HTTPException(status_code=404, detail="Not Found")
    
    raw = f"{solicitacao.cpf}{solicitacao.curso}{datetime.utcnow()}"
    hash_code = hashlib.sha256(raw.encode()).hexdigest()

    solicitacao.hash_blockchain = "0x" + hash_code
    solicitacao.status = "REGISTRADO_BLOCKCHAIN"
    etapas_atualizadas = solicitacao.etapas or []
    etapas_atualizadas.append({"blockchain": {"status": "registrado", "hash": solicitacao.hash_blockchain}})
    solicitacao.etapas = etapas_atualizadas
    db.commit()

    return {"hash": solicitacao.hash_blockchain}


@app.get("/exportar/plataformas")
def exportar_plataformas(cpf: str, solicitacao_id: Optional[int] = None):
    """Mock de exportação ágil dos dados para APOLO, SIC e EMEC."""
    bundle = {
        "APOLO": {"status": "gerado", "protocolo": f"AP-{cpf.replace('.', '').replace('-', '')[:6]}", "url": f"https://apolo.crea-rs.gov.br/registro/{cpf}"},
        "SIC": {"status": "gerado", "protocolo": f"SC-{int(time.time())}", "url": f"https://sic.crea-rs.gov.br/dossie/{cpf}"},
        "EMEC": {"status": "consulta", "url": f"https://emec.mec.gov.br/consulta?cpf={cpf}"},
    }
    return {"cpf": cpf, "solicitacao_id": solicitacao_id, "plataformas": bundle, "msg": "Pacote pronto para conferência humana."}


# Rota 5: Captura e verificação de assinatura manual
@app.post("/assinatura/processar")
async def processar_assinatura(file: UploadFile = File(...)):
    """Simula o recorte e verificação de contraste da assinatura em caneta preta."""
    conteudo = await file.read()
    hash_assinatura = hashlib.sha256(conteudo or b"sem_dados").hexdigest()
    filename = (file.filename or "").lower()

    tinta_preta_detectada = "preta" in filename or hash_assinatura[-1] in {"0", "2", "4", "6", "8"}
    pronta_para_recorte = tinta_preta_detectada and len(conteudo) > 0

    mensagem = (
        "Assinatura detectada em preto sobre área clara. Recorte digital pronto para impressão na carteirinha."
        if pronta_para_recorte
        else "Assinatura com contraste insuficiente. Utilize caneta preta dentro da área pontilhada e reenvie."
    )

    return {
        "valid": pronta_para_recorte,
        "tinta": "preta" if tinta_preta_detectada else "indefinida",
        "recorte_recomendado": "1200x350px (zona central)",
        "hash_assinatura": f"SIG-{hash_assinatura[:20]}",
        "msg": mensagem,
    }


@app.post("/assinatura/comparar")
async def comparar_assinatura(
    assinatura: UploadFile = File(...),
    documento: UploadFile = File(...)
):
    """Compara assinatura enviada com assinatura presente no documento escaneado."""
    assinatura_bytes = await assinatura.read()
    documento_bytes = await documento.read()

    if not assinatura_bytes or not documento_bytes:
        raise HTTPException(status_code=400, detail="Arquivos ausentes para comparação")

    hash_assinatura = hashlib.sha256(assinatura_bytes).hexdigest()
    hash_documento = hashlib.sha256(documento_bytes).hexdigest()
    similaridade = 100 - (abs(int(hash_assinatura, 16) - int(hash_documento, 16)) % 35)
    similaridade = max(12, min(similaridade, 98))

    return {
        "match_score": similaridade,
        "referencia": f"DOC-{hash_documento[:10]}",
        "assinatura_hash": f"SIG-{hash_assinatura[:10]}",
        "alerta": "Assinatura divergente. Encaminhar para conferência humana." if similaridade < 60 else None,
    }


@app.get("/instituicoes/catalogo")
def catalogo_instituicoes(curso: Optional[str] = None):
    """Retorna catálogo rápido de instituições e atribuições para agilizar conferência."""
    base = [
        {"instituicao": "UFRGS", "cursos": ["Engenharia Civil", "Engenharia Elétrica"], "atribuicoes": "CREA nível pleno"},
        {"instituicao": "PUCRS", "cursos": ["Engenharia de Software"], "atribuicoes": "CREA computação"},
        {"instituicao": "UFSM", "cursos": ["Engenharia Sanitária"], "atribuicoes": "CREA ambiental"},
        {"instituicao": "IFRS", "cursos": ["Tecnologia em Construção"], "atribuicoes": "CREA técnico"},
    ]

    if curso:
        base = [b for b in base if any(curso.lower() in c.lower() for c in b["cursos"])]

    return {"instituicoes": base, "fonte": "Catálogo interno para triagem rápida"}


@app.post("/processos/etapa/salvar")
def salvar_etapa(req: SalvarEtapaRequest, db: Session = Depends(get_db)):
    registrado = _registrar_etapa(req.cpf, req.etapa, req.status, req.detalhes)
    if req.solicitacao_id:
        solicitacao = db.query(Solicitacao).filter(Solicitacao.id == req.solicitacao_id).first()
        if solicitacao:
            etapas = solicitacao.etapas or []
            etapas.append({req.etapa: registrado})
            solicitacao.etapas = etapas
            db.commit()
    return {"ok": True, "etapa": req.etapa, "status": req.status, "cache": _etapas_cache.get(req.cpf, {})}


@app.get("/processos/etapa/obter")
def obter_etapas(cpf: str):
    return {"cpf": cpf, "etapas": _etapas_cache.get(cpf, {})}


@app.post("/crea/externo/curso")
def curso_externo(req: CursoExternoRequest):
    """Fluxo para cursos registrados em outros CREAs/estados sem QR ou código automático."""
    if not req.possui_codigo and not req.contato_instituicao:
        raise HTTPException(status_code=400, detail="Informe e-mail ou telefone da instituição para validação manual")

    mensagem = (
        f"Prezados, solicitamos confirmação do curso {req.curso} do aluno {req.nome} (CPF {req.cpf}) na {req.instituicao}/{req.estado}."
        " Responder com autenticidade e status de registro."
    )
    canais = ["APOLO", "SEI", "SIC", "EMEC"]
    _registrar_etapa(req.cpf, "curso_externo", "aguardando_resposta", {"mensagem": mensagem, "canais": canais})
    return {
        "enviado": True,
        "contato": req.contato_instituicao or "não informado",
        "mensagem": mensagem,
        "canais": canais,
        "proximo_passo": "Aguardar resposta institucional ou encaminhar para validação humana do CREA.",
    }


@app.post("/crea/externo/email/enviar")
def enviar_email_validacao(req: ExternalEmailRequest):
    solicitant_payload = {
        "nome": req.nome,
        "cpf": req.cpf,
        "matricula": req.matricula,
        "data_nascimento": req.data_nascimento,
        "curso": req.curso,
        "carga_horaria": req.carga_horaria,
        "periodo_conclusao": req.periodo_conclusao,
        "data_colacao": req.data_colacao,
    }
    institution_payload = {"nome": req.instituicao, "email": req.email_instituicao}

    envio = send_validation_email(solicitant_payload, institution_payload)
    status = "email_enviado" if envio.get("sent") else "email_simulado"
    detalhes = {
        "envio": envio,
        "limiar": THRESHOLD_CONFIRMATION,
        "referencia": f"CPF {req.cpf}",
    }
    _registrar_etapa(req.cpf, "curso_externo_email", status, detalhes)
    return {"status": status, "detalhes": detalhes}


@app.post("/crea/externo/avaliar_resposta")
def avaliar_resposta(req: AvaliarRespostaRequest):
    analise = analyze_response_content(req.resposta)
    decisao = process_validation_result(analise, req.solicitante_nome or req.cpf)

    status = "deferido" if decisao.get("registro_automatico") else "indeferido"
    detalhes = {
        "fonte": "retorno_instituicao",
        "comentario": decisao.get("notificacao_solicitante") or decisao.get("alerta"),
        "analise": analise,
        "decisao": decisao,
    }
    _registrar_etapa(req.cpf, "curso_externo", status, detalhes)
    return {"status": status, **detalhes}


@app.get("/crea/externo/resposta/simular")
def simular_resposta_externa(cpf: str, solicitante_nome: Optional[str] = None):
    resposta = check_mailbox_for_response()
    analise = analyze_response_content(resposta.get("corpo", ""))
    decisao = process_validation_result(analise, solicitante_nome or cpf)
    status = "deferido" if decisao.get("registro_automatico") else "indeferido"
    detalhes = {
        "fonte": "simulacao_caixa_postal",
        "comentario": decisao.get("notificacao_solicitante") or decisao.get("alerta"),
        "analise": analise,
        "decisao": decisao,
        "resposta": resposta,
    }
    _registrar_etapa(cpf, "curso_externo", status, detalhes)
    return {"status": status, **detalhes}


@app.post("/funcionario/certificados/avaliar")
def avaliar_certificados(req: CertificadosBatch):
    """Pontua certificados de especialização com IA mock e sinaliza revisão humana (<90%)."""

    resultados = [_pontuar_certificado(cert) for cert in req.certificados]
    revisao = [r for r in resultados if r["status"] != "aprovado"]

    return {
        "resultados": resultados,
        "resumo": {
            "total": len(resultados),
            "aprovados": len(resultados) - len(revisao),
            "revisao_humana": len(revisao),
            "limiar": 90,
        },
    }


@app.post("/funcionario/certificados/exportar")
def exportar_certificados(req: CertificadosBatch):
    """Gera CSV pronto para planilha com scores e contatos das instituições."""

    resultados = [_pontuar_certificado(cert) for cert in req.certificados]
    buffer = StringIO()
    fieldnames = ["Solicitante", "CPF", "Certificado", "Instituicao", "Contato", "DocID", "Score", "Status"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for item in resultados:
        writer.writerow(item["planilha_row"])

    csv_content = buffer.getvalue()
    buffer.close()

    return {
        "csv": csv_content,
        "resumo": {
            "total": len(resultados),
            "gerado_em": datetime.utcnow().isoformat(),
            "revisao_humana": len([r for r in resultados if r["status"] != "aprovado"]),
        },
        "resultados": resultados,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
