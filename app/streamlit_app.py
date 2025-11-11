import streamlit as st
import httpx
from datetime import date, datetime, timedelta
import pandas as pd

# Use environment variable or default to localhost:8000
import os
API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="OSINT Planning MVP v3", layout="wide")

if "plan" not in st.session_state:
    st.session_state.plan = {
        "title": "Plano de Inteligência",
        "subject": {"what":"", "who":"", "where":""},
        "time_window": {"start":"", "end":""},
        "user": {"principal":"", "others":"", "depth":"executivo", "secrecy":"publico"},
        "purpose": "",
        "deadline": {"date":"", "urgency":"media"},
        "aspects_essential": [],
        "aspects_known": [],
        "aspects_to_know": [],
        "pirs": [],
        "collection": [],
        "extraordinary": [],
        "security": []
    }

st.title("ROC Planejamento de Inteligência")

steps = [
    "Assunto", "Faixa de Tempo", "Usuário", "Finalidade", "Prazo",
    "Aspectos Essenciais", "Aspectos Conhecidos", "Aspectos a Conhecer",
    "PIRs & Coleta", "Medidas Extraordinárias", "Medidas de Segurança", "Preview", "Revisão & Export"
]

with st.sidebar:
    st.header("Etapas")
    current = st.radio("Navegação", steps, index=0)

plan = st.session_state.plan

def save_list(label, key):
    items = plan.get(key, [])
    v = st.text_input(f"Adicionar item em {label}", key=f"add_{key}")
    if st.button(f"Incluir em {label}"):
        vv = (v or "").strip()
        if vv:
            items.append(vv)
            plan[key] = items
            st.success("Incluído.")
    if items:
        st.write("Itens:")
        for i, val in enumerate(items):
            cols = st.columns([0.9,0.1])
            with cols[0]:
                st.write(f"- {val}")
            with cols[1]:
                if st.button("✖", key=f"del_{key}_{i}"):
                    items.pop(i)
                    plan[key] = items
                    st.rerun()

if current == "Assunto":
    st.subheader("a) Determinar o Assunto (O quê? Quem? Onde?)")
    plan["title"] = st.text_input("Título do Plano", plan["title"] or "Plano de Inteligência")
    c1, c2, c3 = st.columns(3)
    with c1:
        plan["subject"]["what"] = st.text_input("O quê", plan["subject"]["what"])
    with c2:
        plan["subject"]["who"] = st.text_input("Quem", plan["subject"]["who"])
    with c3:
        plan["subject"]["where"] = st.text_input("Onde", plan["subject"]["where"])

elif current == "Faixa de Tempo":
    st.subheader("b) Determinar a Faixa de Tempo")
    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("Início", value=date.today())
        plan["time_window"]["start"] = start.isoformat()
    with c2:
        end = st.date_input("Fim", value=date.today())
        plan["time_window"]["end"] = end.isoformat()
    st.info("Defina o período de análise de acordo com as necessidades do usuário.")

elif current == "Usuário":
    st.subheader("c) Determinar o Usuário do Conhecimento")
    plan["user"]["principal"] = st.text_input("Usuário Principal", plan["user"]["principal"])
    plan["user"]["others"] = st.text_input("Outros Usuários (opcional)", plan["user"]["others"])
    plan["user"]["depth"] = st.selectbox("Nível de Profundidade", ["executivo","gerencial","tecnico"], index=0)
    plan["user"]["secrecy"] = st.selectbox("Nível de Sigilo", ["publico","restrito","confidencial","secreto"], index=0)

elif current == "Finalidade":
    st.subheader("d) Determinar a Finalidade do Conhecimento")
    plan["purpose"] = st.text_area("Finalidade", plan["purpose"], height=150)

elif current == "Prazo":
    st.subheader("e) Determinar o Prazo Disponível")
    c1, c2 = st.columns(2)
    with c1:
        plan["deadline"]["date"] = st.date_input("Data Limite", value=date.today()).isoformat()
    with c2:
        plan["deadline"]["urgency"] = st.selectbox("Urgência", ["baixa","media","alta","critica"], index=1)

elif current == "Aspectos Essenciais":
    st.subheader("f) Identificação dos Aspectos Essenciais do Assunto")
    save_list("Aspectos Essenciais", "aspects_essential")

elif current == "Aspectos Conhecidos":
    st.subheader("g) Identificação dos Aspectos Essenciais Conhecidos")
    save_list("Aspectos Conhecidos", "aspects_known")

elif current == "Aspectos a Conhecer":
    st.subheader("h) Identificação dos Aspectos Essenciais a Conhecer")
    st.caption("Dica: derive daqui os requisitos de coleta/PIR.")
    save_list("Aspectos a Conhecer", "aspects_to_know")

elif current == "PIRs & Coleta":
    st.subheader("PIRs (Requisitos de Inteligência) vinculados aos Aspectos a Conhecer")
    if plan["aspects_to_know"]:
        aspect_options = [f"{i} - {txt}" for i, txt in enumerate(plan["aspects_to_know"])]
        aspect_sel = st.selectbox("Vincular ao Aspecto a Conhecer", aspect_options, index=0)
        q = st.text_input("Pergunta (PIR)")
        pr = st.selectbox("Prioridade", ["baixa","media","alta","critica"], index=1)
        just = st.text_input("Justificativa (opcional)")
        if st.button("Incluir PIR"):
            idx = int(aspect_sel.split(" - ")[0]) if aspect_sel else None
            plan["pirs"].append({"aspect_ref": idx, "question": q, "priority": pr, "justification": just})
            st.success("PIR incluído.")
    else:
        st.info("Adicione Aspectos a Conhecer antes de criar PIRs.")
    if plan["pirs"]:
        st.write("### PIRs cadastrados")
        for i, p in enumerate(plan["pirs"]):
            st.write(f"- **#{i}** [aspecto {p.get('aspect_ref','-')}] — {p.get('question','')} (prio: {p.get('priority','')})")

    st.markdown("---")
    st.subheader("Plano de Coleta")
    if plan["pirs"]:
        pir_opts = [f"{i} - {p.get('question','')[:60]}" for i,p in enumerate(plan["pirs"])]
        sel_pir = st.selectbox("PIR de referência", pir_opts, index=0, key="pir_sel_coleta")
        src = st.text_input("Fonte")
        mth = st.text_input("Método (ex.: API, scraping, consulta pública)")
        freq = st.selectbox("Frequência", ["unico","diario","semanal","mensal"], index=0)
        owner = st.text_input("Responsável")
        sla = st.number_input("SLA (horas)", min_value=0, value=0, step=1)
        if st.button("Incluir Tarefa de Coleta"):
            pir_index = int(sel_pir.split(" - ")[0])
            plan["collection"].append({"pir_index": pir_index, "source": src, "method": mth, "frequency": freq, "owner": owner, "sla_hours": int(sla)})
            st.success("Tarefa de coleta incluída.")
    else:
        st.info("Cadastre pelo menos um PIR para incluir tarefas de coleta.")

elif current == "Medidas Extraordinárias":
    st.subheader("i) Previsão de Medidas Extraordinárias")
    save_list("Medidas Extraordinárias", "extraordinary")

elif current == "Medidas de Segurança":
    st.subheader("j) Adoção de Medidas de Segurança")
    save_list("Medidas de Segurança", "security")

elif current == "Preview":
    st.subheader("Pré-visualização do Plano")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Identificação")
        st.write("**Título:**", plan["title"])
        st.write("**Assunto:**", plan["subject"])
        st.write("**Faixa de Tempo:**", plan["time_window"])
        st.write("**Usuário:**", plan["user"])
        st.write("**Finalidade:**", plan["purpose"])
        st.write("**Prazo:**", plan["deadline"])
    with c2:
        st.markdown("### Estrutura Analítica")
        st.write("**Aspectos Essenciais:**", plan["aspects_essential"])
        st.write("**Aspectos Conhecidos:**", plan["aspects_known"])
        st.write("**Aspectos a Conhecer:**", plan["aspects_to_know"])
        st.write("**PIRs:**", plan.get("pirs", []))
        st.write("**Coleta:**", plan.get("collection", []))
        st.write("**Extraordinárias:**", plan["extraordinary"])
        st.write("**Segurança:**", plan["security"])

    st.markdown("---")
    st.markdown("### KPIs do Plano")
    total_ess = len(plan["aspects_essential"])
    total_known = len(plan["aspects_known"])
    total_to_know = len(plan["aspects_to_know"])
    total_pirs = len(plan.get("pirs", []))
    total_tasks = len(plan.get("collection", []))
    coverage = (total_known / total_ess * 100) if total_ess else 0.0
    linkage = (total_tasks / total_pirs * 100) if total_pirs else 0.0
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Essenciais", total_ess)
    k2.metric("Conhecidos", total_known)
    k3.metric("A Conhecer", total_to_know)
    k4.metric("PIRs", total_pirs)
    k5.metric("Tarefas de Coleta", total_tasks)
    st.caption(f"Coverage (Conhecidos/Essenciais): {coverage:.1f}% — Linkage (Tarefas/PIRs): {linkage:.1f}%")

    st.markdown("### Gantt (simplificado) do Plano de Coleta")
    if total_tasks > 0:
        rows = []
        try:
            dl = datetime.fromisoformat(plan["deadline"].get("date") or "")  # may fail
        except Exception:
            dl = datetime.utcnow()
        for i,t in enumerate(plan.get("collection", [])):
            sla_h = int(t.get("sla_hours",0))
            start = dl - timedelta(hours=sla_h)
            end = dl
            rows.append({"Tarefa": f"PIR{t.get('pir_index','')} - {t.get('source','')}", "Início": start, "Fim": end})
        df = pd.DataFrame(rows)
        st.dataframe(df)
    else:
        st.info("Sem tarefas de coleta para montar o Gantt.")

else:
    st.subheader("Revisão & Export")
    st.json(plan)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Salvar Plano (API)"):
            with httpx.Client(timeout=10) as client:
                r = client.post(f"{API_URL}/plans", json=plan)
                if r.status_code == 200:
                    st.success(f"Plano salvo: id {r.json()['id']}")
                    st.session_state.saved_plan = r.json()
                else:
                    st.error(f"Erro ao salvar: {r.text}")
    with col2:
        if st.button("Checar LGPD (API)"):
            saved = st.session_state.get("saved_plan")
            if not saved:
                st.warning("Salve o plano primeiro.")
            else:
                with httpx.Client(timeout=10) as client:
                    r = client.post(f"{API_URL}/plans/{saved['id']}/lgpd_check")
                    st.write(r.json())
    with col3:
        if st.button("Exportar PDF (API)"):
            saved = st.session_state.get("saved_plan")
            if not saved:
                st.warning("Salve o plano primeiro.")
            else:
                with httpx.Client(timeout=10) as client:
                    r = client.get(f"{API_URL}/export/pdf/{saved['id']}")
                    if r.status_code == 200:
                        st.success(f"PDF gerado: {r.json()['file']} (no servidor)")
                    else:
                        st.error(f"Erro ao exportar: {r.text}")
    with col4:
        if st.button("Exportar HTML (API)"):
            saved = st.session_state.get("saved_plan")
            if not saved:
                st.warning("Salve o plano primeiro.")
            else:
                with httpx.Client(timeout=10) as client:
                    r = client.get(f"{API_URL}/export/html/{saved['id']}")
                    if r.status_code == 200:
                        st.success(f"HTML gerado: {r.json()['file']} (no servidor)")
                    else:
                        st.error(f"Erro ao exportar HTML: {r.text}")

    st.markdown("---")
    st.subheader("Evidências (upload → hash)")
    saved = st.session_state.get("saved_plan")
    if not saved:
        st.info("Salve o plano para habilitar o upload de evidências.")
    else:
        up = st.file_uploader("Arquivo de evidência")
        if up is not None:
            with httpx.Client(timeout=60) as client:
                files = {"file": (up.name, up.getvalue())}
                data = {"plan_id": str(saved["id"])}
                r = client.post(f"{API_URL}/evidence/upload", files=files, data=data)
                if r.status_code == 200:
                    st.success(f"Evidência anexada: {r.json()['filename']} (sha256: {r.json()['sha256'][:12]}...)")
                else:
                    st.error(f"Erro no upload: {r.text}")
