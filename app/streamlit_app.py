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
    
    st.markdown("---")
    st.subheader("🔍 Faixa de Tempo (Pesquisa)")
    
    # Initialize research_notes if not exists
    if "plan" in st.session_state and "time_window" in st.session_state.plan:
        if "research_notes" not in st.session_state.plan["time_window"]:
            st.session_state.plan["time_window"]["research_notes"] = ""
    
    # Sidebar notes input
    research_notes = st.text_area(
        "Notas sobre a Pesquisa",
        value=st.session_state.plan["time_window"].get("research_notes", ""),
        height=120,
        placeholder="Contexto, eventos relevantes, restrições de tempo..."
    )
    st.session_state.plan["time_window"]["research_notes"] = research_notes

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
    
    st.markdown("---")
    with st.expander("📖 Guia: Processo de Produção de Conhecimento", expanded=False):
        st.markdown("""
O processo de produção de conhecimento (Inteligência) inicia-se com o acionamento por parte do **DECISOR** ou **DEMANDANTE** (no caso de empresas ou organizações).

**Sequência:**

**DEMANDA** → acionamento  
**ABORDAGEM** → coleta dos dados/informações iniciais (contexto, problema, envolvidos, sistemas, prazos, espaço temporal e ligações)  
**EXECUÇÃO** → NECESSIDADE DE CONHECIMENTOS ⇒ PLANO DE OBTENÇÃO ⇒ EXECUÇÃO DO CICLO DE INTELIGÊNCIA ⇒ PRODUÇÃO DE CONHECIMENTOS ⇒ ENTREGA DOS CONHECIMENTOS

**Processamento:**

### 1ª FASE - PLANEJAMENTO (Identificar e listar a Necessidade de Conhecimentos)

Planejar é conceber a solução para um problema. É combinar arte e ciência para obter a mais precisa compreensão sobre ele, vislumbrando o estado final ou os objetivos que se desejam alcançar quando o problema for resolvido, e estabelecendo formas eficazes para que isso aconteça.

**O bom planejamento facilita:**
- Compreender e desenvolver soluções para os problemas.
- Antecipar eventos e adaptar-se às mudanças de circunstâncias.
- Organizar os meios a sua disposição e priorizar esforços

Dada a natureza incerta e dinâmica das sociedades, o objeto do planejamento não é eliminar a incerteza, mas desenvolver um quadro de ação no meio de tanta incerteza.

Simplificando, o planejar é **pensar de forma crítica e criativa** sobre o que fazer e como fazê-lo para solução de problema(s), enquanto antecipa mudanças ao longo do caminho.

A **1ª Fase - Planejamento de Inteligência**, é a fase na qual o analista de Inteligência, encarregado de produzir um conhecimento, realiza o estudo preliminar e geral do problema e estabelece os procedimentos necessários para cumprir a missão.

**Durante a fase do planejamento, o analista adota os seguintes procedimentos:**

**a) determinação do assunto a ser abordado:**
   
O assunto é, normalmente, definido por meio de uma expressão oral ou escrita, respondendo às seguintes perguntas:
- **O quê?**
- **Quem?**
- **Onde?**
        """)

elif current == "Faixa de Tempo":
    st.subheader("b) Determinar a Faixa de Tempo")
    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("Início", value=date.today())
        plan["time_window"]["start"] = start.isoformat()
    with c2:
        end = st.date_input("Fim", value=date.today())
        plan["time_window"]["end"] = end.isoformat()
    
    st.info("📅 Defina o período de análise de acordo com as necessidades do usuário.\n\n💡 **Dica:** Adicione notas de pesquisa e contexto no campo **Faixa de Tempo (Pesquisa)** no sidebar.")

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
    st.subheader("📋 Revisão & Export")
    
    # Criar abas para melhor organização
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Visualizar", "💾 Salvar & Validar", "📊 Exportar", "📎 Evidências"])
    
    with tab1:
        st.markdown("### Conteúdo do Plano")
        st.json(plan)
    
    with tab2:
        st.markdown("### Gerenciamento do Plano")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💾 Salvar Plano")
            if st.button("🔒 Salvar Plano (API)", key="save_plan", use_container_width=True):
                with st.spinner("Salvando plano..."):
                    with httpx.Client(timeout=10) as client:
                        r = client.post(f"{API_URL}/plans", json=plan)
                        if r.status_code == 200:
                            st.session_state.saved_plan = r.json()
                            st.success(f"✅ Plano salvo com sucesso! ID: **{r.json()['id']}**")
                        else:
                            st.error(f"❌ Erro ao salvar: {r.text}")
            
            # Mostrar status do plano salvo
            saved = st.session_state.get("saved_plan")
            if saved:
                st.info(f"📌 Plano atual: ID **{saved['id']}**")
        
        with col2:
            st.markdown("#### ✅ Validação LGPD")
            if st.button("🛡️ Checar Conformidade LGPD", key="check_lgpd", use_container_width=True):
                saved = st.session_state.get("saved_plan")
                if not saved:
                    st.warning("⚠️ Salve o plano primeiro para validar LGPD.")
                else:
                    with st.spinner("Validando conformidade LGPD..."):
                        with httpx.Client(timeout=10) as client:
                            r = client.post(f"{API_URL}/plans/{saved['id']}/lgpd_check")
                            result = r.json()
                            
                            # Mostrar resultado com cores
                            if result.get("compliant"):
                                st.success("✅ Plano está em conformidade com LGPD!")
                            else:
                                st.error("❌ Plano NÃO está em conformidade com LGPD!")
                            
                            # Expandir detalhes
                            with st.expander("📋 Detalhes da Validação"):
                                st.json(result)
    
    with tab3:
        st.markdown("### Exportar Relatório")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📄 Exportar PDF")
            if st.button("📥 Gerar PDF", key="export_pdf_btn", use_container_width=True):
                saved = st.session_state.get("saved_plan")
                if not saved:
                    st.warning("⚠️ Salve o plano primeiro para exportar PDF.")
                else:
                    with st.spinner("Gerando PDF..."):
                        with httpx.Client(timeout=10) as client:
                            r = client.get(f"{API_URL}/export/pdf/{saved['id']}")
                            if r.status_code == 200:
                                st.session_state.pdf_content = r.content
                                st.session_state.pdf_filename = f"plan_{saved['id']}.pdf"
                                st.success("✅ PDF gerado com sucesso!")
                            else:
                                st.error(f"❌ Erro ao exportar: {r.text}")
            
            # Botão de download se PDF foi gerado
            if "pdf_content" in st.session_state:
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=st.session_state.pdf_content,
                    file_name=st.session_state.pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col2:
            st.markdown("#### 🌐 Exportar HTML")
            if st.button("📥 Gerar HTML", key="export_html_btn", use_container_width=True):
                saved = st.session_state.get("saved_plan")
                if not saved:
                    st.warning("⚠️ Salve o plano primeiro para exportar HTML.")
                else:
                    with st.spinner("Gerando HTML..."):
                        with httpx.Client(timeout=10) as client:
                            r = client.get(f"{API_URL}/export/html/{saved['id']}")
                            if r.status_code == 200:
                                st.session_state.html_content = r.content
                                st.session_state.html_filename = f"plan_{saved['id']}.html"
                                st.success("✅ HTML gerado com sucesso!")
                            else:
                                st.error(f"❌ Erro ao exportar: {r.text}")
            
            # Botão de download se HTML foi gerado
            if "html_content" in st.session_state:
                st.download_button(
                    label="⬇️ Baixar HTML",
                    data=st.session_state.html_content,
                    file_name=st.session_state.html_filename,
                    mime="text/html",
                    use_container_width=True
                )
    
    with tab4:
        st.markdown("### Gerenciar Evidências")
        saved = st.session_state.get("saved_plan")
        if not saved:
            st.info("💡 Salve o plano para habilitar o upload de evidências.")
        else:
            st.markdown("#### 📎 Upload de Arquivo")
            up = st.file_uploader("Selecione um arquivo de evidência", key=f"uploader_{saved['id']}")
            if up is not None:
                if st.button("⬆️ Enviar Evidência", key=f"upload_btn_{saved['id']}", use_container_width=True):
                    with st.spinner("Calculando hash e enviando..."):
                        with httpx.Client(timeout=60) as client:
                            files = {"file": (up.name, up.getvalue())}
                            data = {"plan_id": str(saved["id"])}
                            r = client.post(f"{API_URL}/evidence/upload", files=files, data=data)
                            if r.status_code == 200:
                                result = r.json()
                                st.success(f"✅ Evidência anexada com sucesso!")
                                st.info(f"📄 **{result['filename']}** → SHA-256: `{result['sha256']}`")
                            else:
                                st.error(f"❌ Erro no upload: {r.text}")
