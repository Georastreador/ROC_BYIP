from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .db.database import SessionLocal, engine, Base
from .models.models import Plan, Evidence
from .schemas.schemas import PlanCreate, PlanRead, EvidenceRead
from .services.audit import log as audit_log
from .services.lgpd import lgpd_check
from .services.pdf import generate_plan_pdf
import json, os, hashlib, base64, datetime

Base.metadata.create_all(bind=engine)
app = FastAPI(title="OSINT Planning API v3")

API_KEY = os.environ.get("API_KEY", "devkey")
REQUIRE_API_KEY = os.environ.get("REQUIRE_API_KEY", "false").lower() == "true"

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
def health():
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
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
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
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    evs = db.query(Evidence).filter(Evidence.plan_id==plan.id).all()
    return _to_read(plan, evidences=evs)

@app.get("/plans", response_model=list[PlanRead])
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).order_by(Plan.id.desc()).all()
    result = []
    for p in plans:
        evs = db.query(Evidence).filter(Evidence.plan_id==p.id).all()
        result.append(_to_read(p, evidences=evs))
    return result

@app.post("/plans/{plan_id}/lgpd_check")
def check_lgpd(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    data = _to_dict(plan)
    result = lgpd_check(data)
    audit_log(db, action="lgpd_check", detail=str(result), plan_id=plan.id)
    return result

@app.get("/export/pdf/{plan_id}")
def export_pdf(plan_id: int, db: Session = Depends(get_db)):
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
def export_html(plan_id: int, db: Session = Depends(get_db)):
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
  <div class="card"><b>Assunto:</b> <span class="mono">{json.dumps(data.get('subject',{}), ensure_ascii=False)}</span></div>
  <div class="card"><b>Faixa de Tempo:</b> <span class="mono">{json.dumps(data.get('time_window',{}), ensure_ascii=False)}</span></div>
  <div class="card"><b>Usuário:</b> <span class="mono">{json.dumps(data.get('user',{}), ensure_ascii=False)}</span></div>
  <div class="card"><b>Finalidade:</b> {data.get('purpose','')}</div>
  <div class="card"><b>Prazo:</b> <span class="mono">{json.dumps(data.get('deadline',{}), ensure_ascii=False)}</span></div>
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
async def upload_evidence(plan_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    os.makedirs("uploads", exist_ok=True)
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    path = os.path.join("uploads", file.filename)
    with open(path, "wb") as f:
        f.write(content)
    ev = Evidence(plan_id=plan.id, filename=file.filename, sha256=sha256, size=len(content))
    db.add(ev)
    db.commit()
    db.refresh(ev)
    audit_log(db, action="upload_evidence", detail=f"{file.filename} {sha256}", plan_id=plan.id)
    return EvidenceRead(id=ev.id, filename=ev.filename, sha256=ev.sha256, size=ev.size)
