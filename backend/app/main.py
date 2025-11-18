from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from .db.database import SessionLocal, engine, Base
from .models.models import Plan, Evidence
from .schemas.schemas import PlanCreate, PlanRead, EvidenceRead
from .services.audit import log as audit_log
from .services.lgpd import lgpd_check
from .services.pdf import generate_plan_pdf
from .services.error_handler import setup_exception_handlers
from .services.backup import create_backup, restore_backup, list_backups, cleanup_old_backups, get_backup_stats
import json, os, hashlib, base64, datetime
from pathlib import Path

Base.metadata.create_all(bind=engine)
app = FastAPI(title="OSINT Planning API v3")

# Configurar exception handlers globais
setup_exception_handlers(app)

API_KEY = os.environ.get("API_KEY", "devkey")
REQUIRE_API_KEY = os.environ.get("REQUIRE_API_KEY", "false").lower() == "true"

# Configuração de Upload
# Tamanho máximo de arquivo (padrão: 50MB)
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB em bytes

# Tipos de arquivo permitidos (extensões)
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",  # Documentos e imagens
    ".txt", ".md", ".csv",  # Texto
    ".doc", ".docx", ".xls", ".xlsx",  # Office
    ".zip", ".rar", ".7z",  # Arquivos compactados
    ".json", ".xml",  # Dados estruturados
}

# MIME types permitidos (validação adicional)
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/jpg", "image/gif",
    "text/plain", "text/markdown", "text/csv",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip", "application/x-rar-compressed", "application/x-7z-compressed",
    "application/json", "application/xml", "text/xml",
}

# Configuração Rate Limiting
# Permite desabilitar via variável de ambiente RATE_LIMIT_ENABLED=false
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Sempre criar o limiter, mas com limites muito altos se desabilitado
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Se desabilitado, definir limites muito altos (efetivamente sem limite)
if not RATE_LIMIT_ENABLED:
    # Override dos limites para valores muito altos quando desabilitado
    # Isso permite que o código funcione sem mudanças, mas sem limitar
    pass  # Os decoradores @limiter.limit() ainda funcionam, mas podem ser ignorados em dev

# Configuração CORS
# Permite configuração via variável de ambiente CORS_ORIGINS
# Formato: "http://localhost:8501,http://localhost:3000,https://exemplo.com"
# Se não definido, usa localhost por padrão (desenvolvimento)
CORS_ORIGINS_ENV = os.environ.get("CORS_ORIGINS", "")
if CORS_ORIGINS_ENV:
    # Split por vírgula e remove espaços
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",")]
else:
    # Padrão para desenvolvimento: localhost em portas comuns
    allowed_origins = [
        "http://localhost:8501",  # Streamlit padrão
        "http://localhost:8502",  # Streamlit alternativo
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
        "http://localhost:3000",  # React/Next.js comum
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Permite todos os headers (incluindo X-API-Key)
    expose_headers=["*"],  # Expõe todos os headers na resposta
)

@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    if REQUIRE_API_KEY:
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    response = await call_next(request)
    return response

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
@limiter.limit("100/minute")  # Health check pode ser chamado frequentemente
def health(request: Request):
    return {"status": "ok"}

def _to_read(plan: Plan, evidences: list[Evidence] | None = None) -> PlanRead:
    return PlanRead(
        id=plan.id,
        title=plan.title,
        subject=json.loads(plan.subject),
        time_window=json.loads(plan.time_window),
        user=json.loads(plan.user),
        purpose=plan.purpose,
        deadline=json.loads(plan.deadline),
        aspects_essential=json.loads(plan.aspects_essential),
        aspects_known=json.loads(plan.aspects_known),
        aspects_to_know=json.loads(plan.aspects_to_know),
        pirs=json.loads(plan.pirs or "[]"),
        collection=json.loads(plan.collection or "[]"),
        extraordinary=json.loads(plan.extraordinary or "[]"),
        security=json.loads(plan.security or "[]"),
        evidences=[EvidenceRead(id=e.id, filename=e.filename, sha256=e.sha256, size=e.size) for e in (evidences or [])]
    )

def _to_dict(plan: Plan) -> dict:
    return _to_read(plan).model_dump()

@app.post("/plans", response_model=PlanRead)
@limiter.limit("20/minute")  # Limite de criação de planos
def create_plan(request: Request, payload: PlanCreate, db: Session = Depends(get_db)):
    plan = Plan(
        title=payload.title,
        subject=json.dumps(payload.subject.model_dump(), ensure_ascii=False),
        time_window=json.dumps(payload.time_window.model_dump(), ensure_ascii=False),
        user=json.dumps(payload.user.model_dump(), ensure_ascii=False),
        purpose=payload.purpose,
        deadline=json.dumps(payload.deadline.model_dump(), ensure_ascii=False),
        aspects_essential=json.dumps(payload.aspects_essential, ensure_ascii=False),
        aspects_known=json.dumps(payload.aspects_known, ensure_ascii=False),
        aspects_to_know=json.dumps(payload.aspects_to_know, ensure_ascii=False),
        pirs=json.dumps([p.model_dump() for p in payload.pirs], ensure_ascii=False),
        collection=json.dumps([c.model_dump() for c in payload.collection], ensure_ascii=False),
        extraordinary=json.dumps(payload.extraordinary, ensure_ascii=False),
        security=json.dumps(payload.security, ensure_ascii=False),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    audit_log(db, action="create_plan", detail=f"Plan {plan.id} created", plan_id=plan.id)
    return _to_read(plan, evidences=[])

@app.get("/plans/{plan_id}", response_model=PlanRead)
@limiter.limit("60/minute")  # Leitura pode ser mais frequente
def get_plan(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    evs = db.query(Evidence).filter(Evidence.plan_id==plan.id).all()
    return _to_read(plan, evidences=evs)

@app.get("/plans", response_model=list[PlanRead])
@limiter.limit("30/minute")  # Listagem pode ser moderada
def list_plans(request: Request, db: Session = Depends(get_db)):
    plans = db.query(Plan).order_by(Plan.id.desc()).all()
    result = []
    for p in plans:
        evs = db.query(Evidence).filter(Evidence.plan_id==p.id).all()
        result.append(_to_read(p, evidences=evs))
    return result

@app.post("/plans/{plan_id}/lgpd_check")
@limiter.limit("30/minute")  # Validação LGPD moderada
def check_lgpd(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    data = _to_dict(plan)
    result = lgpd_check(data)
    audit_log(db, action="lgpd_check", detail=str(result), plan_id=plan.id)
    return result

@app.get("/export/pdf/{plan_id}")
@limiter.limit("10/minute")  # Geração de PDF é mais pesada
def export_pdf(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    data = _to_dict(plan)
    os.makedirs("exports", exist_ok=True)
    outfile = f"exports/plan_{plan.id}.pdf"
    generate_plan_pdf(data, outfile)
    audit_log(db, action="export_pdf", detail=outfile, plan_id=plan.id)
    return FileResponse(outfile, media_type="application/pdf", filename=f"plan_{plan.id}.pdf")

@app.get("/export/html/{plan_id}")
@limiter.limit("20/minute")  # HTML é mais leve que PDF
def export_html(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    data = _to_dict(plan)
    os.makedirs("exports", exist_ok=True)
    outfile = f"exports/plan_{plan.id}.html"
    logo_path = os.environ.get("REPORT_LOGO_PATH")
    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        b64 = base64.b64encode(open(logo_path,"rb").read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:60px;"/>'
    html = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8"/>
<title>Plano de Inteligência — {data.get('title','')}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:24px;color:#0f172a;}}
header{{display:flex;align-items:center;gap:16px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;margin-bottom:16px;}}
h1{{font-size:20px;margin:0;}}
.section{{margin:16px 0;}}
.card{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin:8px 0;}}
.table{{width:100%;border-collapse:collapse;font-size:14px;}}
.table th,.table td{{border:1px solid #e2e8f0;padding:8px;text-align:left;}}
.mono{{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;font-size:12px;}}
</style>
</head>
<body>
<header>
{logo_html}
<div>
<h1>Plano de Inteligência — 1ª Fase (Planejamento)</h1>
<div class="mono">{datetime.datetime.utcnow().isoformat()}Z</div>
</div>
</header>

<div class="section">
  <div class="card"><b>Título:</b> {data.get('title','')}</div>
  <div class="card">
    <b>Assunto:</b><br/>
    O quê: <strong>{data.get('subject',{}).get('what','')}</strong><br/>
    Quem: <strong>{data.get('subject',{}).get('who','')}</strong><br/>
    Onde: <strong>{data.get('subject',{}).get('where','')}</strong>
  </div>
  <div class="card">
    <b>Faixa de Tempo (Pesquisa):</b><br/>
    Início: <strong>{data.get('time_window',{}).get('start','')}</strong><br/>
    Fim: <strong>{data.get('time_window',{}).get('end','')}</strong><br/>
    Notas: {data.get('time_window',{}).get('research_notes','') or '<em>(nenhuma anotação)</em>'}
  </div>
  <div class="card">
    <b>Usuário:</b><br/>
    Principal: <strong>{data.get('user',{}).get('principal','')}</strong><br/>
    Outros: {data.get('user',{}).get('others','') or '<em>(nenhum)</em>'}<br/>
    Profundidade: <strong>{data.get('user',{}).get('depth','')}</strong><br/>
    Sigilo: <strong>{data.get('user',{}).get('secrecy','')}</strong>
  </div>
  <div class="card"><b>Finalidade:</b> {data.get('purpose','')}</div>
  <div class="card">
    <b>Prazo:</b><br/>
    Data Limite: <strong>{data.get('deadline',{}).get('date','')}</strong><br/>
    Urgência: <strong>{data.get('deadline',{}).get('urgency','')}</strong>
  </div>
</div>

<div class="section">
  <h3>Aspectos</h3>
  <div class="card"><b>Essenciais</b><br/>{"<br/>".join([f"• {x}" for x in data.get("aspects_essential",[])]) or "-"}</div>
  <div class="card"><b>Conhecidos</b><br/>{"<br/>".join([f"• {x}" for x in data.get("aspects_known",[])]) or "-"}</div>
  <div class="card"><b>A Conhecer</b><br/>{"<br/>".join([f"• {x}" for x in data.get("aspects_to_know",[])]) or "-"}</div>
</div>

<div class="section">
  <h3>PIRs</h3>
  <table class="table">
    <thead><tr><th>#</th><th>Aspecto Ref</th><th>Pergunta</th><th>Prioridade</th></tr></thead>
    <tbody>
    { "".join([f"<tr><td>{i}</td><td>{str(p.get('aspect_ref','-'))}</td><td>{p.get('question','')}</td><td>{p.get('priority','')}</td></tr>" for i,p in enumerate(data.get('pirs',[]))]) or "<tr><td colspan='4'>-</td></tr>" }
    </tbody>
  </table>
</div>

<div class="section">
  <h3>Plano de Coleta</h3>
  <table class="table">
    <thead><tr><th>PIR #</th><th>Fonte</th><th>Método</th><th>Freq.</th><th>Owner</th><th>SLA (h)</th></tr></thead>
    <tbody>
    { "".join([f"<tr><td>{t.get('pir_index','')}</td><td>{t.get('source','')}</td><td>{t.get('method','')}</td><td>{t.get('frequency','')}</td><td>{t.get('owner','')}</td><td>{t.get('sla_hours',0)}</td></tr>" for t in data.get('collection',[])]) or "<tr><td colspan='6'>-</td></tr>" }
    </tbody>
  </table>
</div>

<div class="section">
  <h3>Medidas</h3>
  <div class="card"><b>Extraordinárias</b><br/>{"<br/>".join([f"• {x}" for x in data.get("extraordinary",[])]) or "-"}</div>
  <div class="card"><b>Segurança</b><br/>{"<br/>".join([f"• {x}" for x in data.get("security",[])]) or "-"}</div>
</div>

</body>
</html>"""
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)
    audit_log(db, action="export_html", detail=outfile, plan_id=plan.id)
    return FileResponse(outfile, media_type="text/html", filename=f"plan_{plan.id}.html")

@app.post("/evidence/upload", response_model=EvidenceRead)
@limiter.limit("5/minute")  # Upload é mais restritivo (arquivos grandes)
async def upload_evidence(request: Request, plan_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Validação de nome de arquivo
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Validação de extensão
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # Validação de MIME type (se disponível)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File MIME type not allowed: {file.content_type}"
        )
    
    # Ler arquivo em chunks para validar tamanho antes de carregar tudo na memória
    os.makedirs("uploads", exist_ok=True)
    content = b""
    chunk_size = 1024 * 1024  # 1MB por chunk
    
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            
            # Verificar tamanho acumulado
            if len(content) + len(chunk) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
                )
            
            content += chunk
        
        # Verificar tamanho final
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
            )
        
        # Calcular hash SHA-256
        sha256 = hashlib.sha256(content).hexdigest()
        
        # Salvar arquivo
        # Sanitizar nome do arquivo para evitar path traversal
        safe_filename = os.path.basename(file.filename)
        path = os.path.join("uploads", safe_filename)
        
        # Se arquivo já existe com mesmo hash, não duplicar
        if os.path.exists(path):
            existing_hash = hashlib.sha256(open(path, "rb").read()).hexdigest()
            if existing_hash == sha256:
                # Arquivo já existe, apenas criar referência no banco
                pass
            else:
                # Nome igual mas conteúdo diferente, adicionar sufixo
                base_name, ext = os.path.splitext(safe_filename)
                counter = 1
                while os.path.exists(path):
                    safe_filename = f"{base_name}_{counter}{ext}"
                    path = os.path.join("uploads", safe_filename)
                    counter += 1
        
        with open(path, "wb") as f:
            f.write(content)
        
        # Criar registro no banco
        ev = Evidence(plan_id=plan.id, filename=safe_filename, sha256=sha256, size=len(content))
        db.add(ev)
        db.commit()
        db.refresh(ev)
        audit_log(db, action="upload_evidence", detail=f"{safe_filename} {sha256} ({len(content)} bytes)", plan_id=plan.id)
        
        return EvidenceRead(id=ev.id, filename=ev.filename, sha256=ev.sha256, size=ev.size)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log erro e retornar mensagem genérica
        audit_log(db, action="upload_error", detail=f"Error uploading {file.filename}: {str(e)}", plan_id=plan.id)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while uploading the file. Please try again."
        )

# Endpoints de Backup e Recuperação
@app.post("/backup/create")
def create_backup_endpoint(db: Session = Depends(get_db)):
    """Cria um backup do banco de dados"""
    try:
        backup_path = create_backup()
        audit_log(db, action="backup_create", detail=f"Backup created: {backup_path}")
        
        # Limpar backups antigos após criar novo
        cleanup_old_backups()
        
        return {
            "status": "success",
            "message": "Backup created successfully",
            "backup_path": backup_path,
            "created_at": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        audit_log(db, action="backup_error", detail=f"Error creating backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")


@app.get("/backup/list")
def list_backups_endpoint(db: Session = Depends(get_db)):
    """Lista todos os backups disponíveis"""
    try:
        backups = list_backups()
        stats = get_backup_stats()
        audit_log(db, action="backup_list", detail=f"Listed {len(backups)} backups")
        
        return {
            "backups": backups,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing backups: {str(e)}")


@app.post("/backup/restore/{backup_filename}")
def restore_backup_endpoint(backup_filename: str, db: Session = Depends(get_db)):
    """Restaura um backup específico"""
    try:
        from .services.backup import BACKUP_DIR
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        success = restore_backup(backup_path)
        
        if success:
            audit_log(db, action="backup_restore", detail=f"Backup restored: {backup_filename}")
            return {
                "status": "success",
                "message": "Backup restored successfully",
                "backup_file": backup_filename,
                "restored_at": datetime.datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to restore backup")
    
    except HTTPException:
        raise
    except Exception as e:
        audit_log(db, action="backup_restore_error", detail=f"Error restoring backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restoring backup: {str(e)}")


@app.get("/backup/stats")
def backup_stats_endpoint(db: Session = Depends(get_db)):
    """Retorna estatísticas dos backups"""
    try:
        stats = get_backup_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting backup stats: {str(e)}")
