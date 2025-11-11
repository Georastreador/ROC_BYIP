from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from datetime import datetime
import json

def _kv_block(c, x, y, title, body, w, h):
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    y -= 16
    c.setFont("Helvetica", 10)
    for line in body.split("\n"):
        c.drawString(x, y, line[:120])
        y -= 14
        if y < 3*cm:
            c.showPage()
            y = h - 2*cm
            c.setFont("Helvetica", 10)
    return y - 8

def generate_plan_pdf(plan: dict, outfile: str):
    c = canvas.Canvas(outfile, pagesize=A4)
    w, h = A4
    x, y = 2*cm, h - 2*cm

    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(0, h-60, w, 60, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, h-40, "Plano de Inteligência — 1ª Fase (Planejamento)")
    c.setFont("Helvetica", 9)
    c.drawRightString(w-2*cm, h-30, datetime.utcnow().isoformat()+"Z")
    c.setFillColor(colors.black)

    y = h - 80
    y = _kv_block(c, x, y, "Título", plan.get("title",""))
    y = _kv_block(c, x, y, "Assunto", json.dumps(plan.get("subject", {}), ensure_ascii=False, indent=2))
    y = _kv_block(c, x, y, "Faixa de Tempo", json.dumps(plan.get("time_window", {}), ensure_ascii=False, indent=2))
    y = _kv_block(c, x, y, "Usuário", json.dumps(plan.get("user", {}), ensure_ascii=False, indent=2))
    y = _kv_block(c, x, y, "Finalidade", plan.get("purpose",""))
    y = _kv_block(c, x, y, "Prazo", json.dumps(plan.get("deadline", {}), ensure_ascii=False, indent=2))

    def list_to_text(lst):
        return "\n".join([f"• {i}" for i in lst]) if lst else "-"

    sections = [
        ("Aspectos Essenciais", list_to_text(plan.get("aspects_essential",[]))),
        ("Aspectos Conhecidos", list_to_text(plan.get("aspects_known",[]))),
        ("Aspectos a Conhecer", list_to_text(plan.get("aspects_to_know",[]))),
        ("Medidas Extraordinárias", list_to_text(plan.get("extraordinary",[]))),
        ("Medidas de Segurança", list_to_text(plan.get("security",[]))),
    ]
    for title, body in sections:
        y = _kv_block(c, x, y, title, body, w, h)
        if y < 3*cm:
            c.showPage(); y = h - 2*cm

    pirs = plan.get("pirs", [])
    if pirs:
        c.showPage()
        y = h - 2*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "PIRs (Requisitos de Inteligência)")
        y -= 20
        data = [["#", "Aspecto Ref", "Pergunta", "Prioridade"]]
        for i, p in enumerate(pirs):
            data.append([str(i), str(p.get("aspect_ref","-")), p.get("question",""), p.get("priority","")])
        table = Table(data, colWidths=[1.2*cm, 3*cm, 10*cm, 3*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#E2E8F0")),
            ("GRID",(0,0),(-1,-1), 0.5, colors.grey),
            ("FONT",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONT",(0,1),(-1,-1),"Helvetica"),
        ]))
        table.wrapOn(c, w, h)
        table_height = 18 * (len(data))
        table.drawOn(c, x, y - table_height)

    col = plan.get("collection", [])
    if col:
        c.showPage()
        y = h - 2*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Plano de Coleta")
        y -= 20
        data = [["PIR #","Fonte","Método","Freq.","Owner","SLA (h)"]]
        for t in col:
            data.append([str(t.get("pir_index","")), t.get("source",""), t.get("method",""), t.get("frequency",""), t.get("owner",""), str(t.get("sla_hours",0))])
        table = Table(data, colWidths=[2*cm, 4*cm, 5*cm, 2*cm, 3*cm, 2*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#E2E8F0")),
            ("GRID",(0,0),(-1,-1), 0.5, colors.grey),
            ("FONT",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONT",(0,1),(-1,-1),"Helvetica"),
        ]))
        table.wrapOn(c, w, h)
        table_height = 18 * (len(data))
        table.drawOn(c, x, y - table_height)

    c.showPage()
    c.save()
