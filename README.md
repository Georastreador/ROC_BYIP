# ROC Planejamento de Inteligência — MVP v3

Aplicação web para **planejamento sistemático de operações de inteligência** (OSINT) seguindo a metodologia de **Planejamento de Inteligência em 10 fases**.

Arquitetura: **Streamlit** (frontend) + **FastAPI** (backend) + **SQLite** (banco de dados).

## 📋 Características Principais

### Frontend (Streamlit)
- ✅ Interface interativa com **13 etapas de planejamento** estruturadas
- ✅ Coleta de informações: Assunto, Tempo, Usuário, Finalidade, Prazo
- ✅ Análise de Aspectos: Essenciais, Conhecidos, A Conhecer
- ✅ Gerenciamento de **PIRs** (Priority Intelligence Requirements)
- ✅ Planejamento de **Tarefas de Coleta** com SLA
- ✅ Medidas Extraordinárias e de Segurança
- ✅ **Pré-visualização** com KPIs e Gantt simplificado
- ✅ Exportação em **PDF** e **HTML** (com logotipo personalizado)
- ✅ **Upload de evidências** com hash SHA-256

### Backend (FastAPI)
- ✅ API RESTful para gerenciar Planos de Inteligência
- ✅ Persistência em **SQLite**
- ✅ **Validação LGPD** automática (sigilo e medidas de segurança)
- ✅ **Auditoria** de todas as ações
- ✅ Geração de relatórios em **PDF** e **HTML**
- ✅ Gerenciamento de **evidências** (upload + hash)
- ✅ **Segurança** com API Key opcional (`REQUIRE_API_KEY`, `API_KEY`)
- ✅ Health check (`/health`)

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.10+
- pip ou conda

### ⚡ Execução Rápida (One-Click para Usuários)

Se você é um **usuário não-técnico** e quer rodar a aplicação rapidamente:

#### macOS
```bash
# Duplo clique em:
./run_app.command

# Ou execute via terminal:
bash run_app.command
```

#### Windows
```bash
# Duplo clique em:
run_app.bat

# Ou execute via cmd:
run_app.bat
```

✅ Isso iniciará automaticamente:
- Backend (FastAPI) na porta 8000
- Frontend (Streamlit) na porta 8501 (ou 8502 se 8501 estiver ocupada)
- Verificará dependências e criará ambiente virtual, se necessário
- Limpará portas ocupadas automaticamente

Acesse: **http://localhost:8501** (ou a porta exibida)

**Nota:** Scripts disponíveis apenas após clonar o repositório. Para mais detalhes, veja `GETTING_STARTED_FOR_USERS.md`.

---

### 1. Clonar e Preparar Ambiente

```bash
cd /Users/rikardocroce/Library/CloudStorage/OneDrive-Personal/# ROC project Dsvn/BYIP/intel_planning_osint_mvp_v3
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 2. Instalar Dependências

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../app
pip install -r requirements.txt
```

### 3. Iniciar o Backend (FastAPI)

```bash
cd backend
export REPORT_LOGO_PATH=/caminho/para/logo.png  # (opcional)
export REQUIRE_API_KEY=true  # (opcional)
export API_KEY=seu_token_secreto  # (opcional)

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse: **http://localhost:8000**
- Documentação Swagger: **http://localhost:8000/docs**
- Documentação ReDoc: **http://localhost:8000/redoc**

### 4. Iniciar o Frontend (Streamlit) — Em outro terminal

```bash
cd app
streamlit run streamlit_app.py
```

Acesse: **http://localhost:8501**

## 📊 Estrutura do Projeto

```
.
├── README.md                          # Este arquivo
├── RUNNING.md                         # Instruções de execução
├── Makefile                           # Comandos auxiliares
├── pytest.ini                         # Configuração de testes
│
├── app/                               # Frontend (Streamlit)
│   ├── streamlit_app.py              # Aplicação principal
│   └── requirements.txt               # Dependências
│
├── backend/                           # Backend (FastAPI)
│   ├── requirements.txt               # Dependências
│   └── app/
│       ├── main.py                    # Aplicação FastAPI (rotas)
│       ├── db/
│       │   └── database.py            # Configuração SQLite + SessionLocal
│       ├── models/
│       │   └── models.py              # SQLAlchemy models (Plan, Evidence, AuditLog)
│       ├── schemas/
│       │   └── schemas.py             # Pydantic schemas (PlanCreate, PlanRead, etc.)
│       └── services/
│           ├── audit.py               # Logging de auditoria
│           ├── lgpd.py                # Validação de conformidade LGPD
│           └── pdf.py                 # Geração de relatórios PDF
│
└── tests/
    ├── __init__.py
    ├── test_api.py                    # Testes unitários da API
    └── ...
```

## � Preparar para subir ao GitHub

Antes de subir o projeto para o repositório remoto, verifique os itens abaixo e siga os comandos recomendados.

1) Verifique `.gitignore` (já fornecido) para não comitar arquivos sensíveis como `.env`, `backend/app.db`, `BYIP_BkUp/` e diretórios de ambiente/IDE.

2) Se ainda não há repositório Git local, inicialize e faça o primeiro commit:

```bash
# no diretório raiz do projeto
git init
git add .
git commit -m "chore: initial project import"
```

3) Conectar ao repositório remoto (substitua se necessário):

```bash
git remote add origin https://github.com/Georastreador/ROC_BYIP.git
git branch -M main
git push -u origin main
```

Observações importantes:
- Não faça push de arquivos sensíveis. Use `.env` e `backend/.env` locais e mantenha-os fora do repositório.
- Se sua organização usar branch diferente (ex.: `master`), ajuste os comandos acima.
- Para autenticar o push, use suas credenciais GitHub ou um token pessoal (PAT) com permissões adequadas.

Se preferir, crie um fork/branch para desenvolvimento colaborativo e abra Pull Requests para integrar mudanças ao repositório remoto principal.


## �🔌 API REST — Endpoints Principais

### Planos de Inteligência

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/plans` | Criar novo plano |
| `GET` | `/plans` | Listar todos os planos |
| `GET` | `/plans/{plan_id}` | Obter plano por ID |
| `POST` | `/plans/{plan_id}/lgpd_check` | Validar conformidade LGPD |

### Exportação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/export/pdf/{plan_id}` | Exportar plano em PDF |
| `GET` | `/export/html/{plan_id}` | Exportar plano em HTML |

### Evidências

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/evidence/upload` | Fazer upload de arquivo + calcular SHA-256 |

### Sistema

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/health` | Health check |

## 📝 Exemplo de Uso — Fluxo Completo

### 1. Acessar Streamlit
```bash
streamlit run app/streamlit_app.py
```

### 2. Preencher o Formulário (13 etapas)
- **Etapa 1 (Assunto):** Título, O quê?, Quem?, Onde?
- **Etapa 2 (Tempo):** Data início e fim
- **Etapa 3 (Usuário):** Usuário principal, nível de profundidade, sigilo
- **Etapa 4 (Finalidade):** Descrição do objetivo
- **Etapa 5 (Prazo):** Data limite + urgência
- **Etapas 6-10:** Aspectos (Essenciais, Conhecidos, A Conhecer), PIRs, Coleta
- **Etapas 11-12:** Medidas (Extraordinárias, Segurança)
- **Etapa 13 (Preview):** KPIs, Gantt e opções de export

### 3. Salvar Plano
Clique em **"Salvar Plano (API)"** → plano é persistido no banco e ID é exibido

### 4. Validar LGPD
Clique em **"Checar LGPD (API)"** → validação de conformidade é exibida em painel expansível

### 5. Exportar Relatório
Interface com abas para maior clareza:

#### Aba: Exportar
- **PDF:** 
  1. Clique em **"📥 Gerar PDF"** → arquivo é gerado no servidor
  2. Clique em **"⬇️ Baixar PDF"** → arquivo é baixado no seu computador
  
- **HTML:**
  1. Clique em **"📥 Gerar HTML"** → arquivo é gerado no servidor
  2. Clique em **"⬇️ Baixar HTML"** → arquivo é baixado no seu computador

✅ **Novo:** Downloads diretos no navegador (sem salvar no servidor)

### 6. Anexar Evidências
#### Aba: Evidências
- Após salvar o plano, faça upload de arquivos
- SHA-256 é calculado automaticamente
- Arquivo é vinculado ao plano

## 🔐 Segurança

### API Key (Opcional)
```bash
export REQUIRE_API_KEY=true
export API_KEY=seu_token_secreto
```

Incluir no header da requisição:
```bash
curl -H "X-API-Key: seu_token_secreto" http://localhost:8000/plans
```

### Validação LGPD
- ✅ Verifica nível de sigilo vs. medidas de segurança
- ✅ Valida faixa de tempo
- ✅ Exige aspectos a conhecer quando essenciais estão definidos

### Auditoria
- Todas as ações (create, read, export, upload) são registradas em `audit_logs`
- Actor, timestamp, action, detail e plan_id são rastreados

## 📦 Dependências

### Frontend (`app/requirements.txt`)
```
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
SQLAlchemy==2.0.35
reportlab==4.2.5
streamlit==1.39.0
httpx==0.27.2
python-multipart==0.0.12
```

### Backend (`backend/requirements.txt`)
- Mesmas dependências (projeto unificado)

## 🧪 Testes

```bash
pytest tests/ -v
```

## 🛠 Makefile — Comandos Auxiliares

```bash
make run-backend    # Inicia Backend (FastAPI)
make run-frontend   # Inicia Frontend (Streamlit)
make test          # Executa testes
make clean         # Remove cache e arquivos temporários
```

## 🌐 Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `API_URL` | URL do backend (frontend) | `http://localhost:8000` |
| `REQUIRE_API_KEY` | Ativar API Key | `false` |
| `API_KEY` | Token de segurança | `devkey` |
| `REPORT_LOGO_PATH` | Caminho do logo (PDF/HTML) | ` ` (vazio) |

## 📚 Metodologia — Planejamento de Inteligência (a→j)

A aplicação segue a estrutura de **10 fases** de um Plano de Inteligência:

1. **a) Assunto** — O quê, quem, onde
2. **b) Faixa de Tempo** — Período de análise
3. **c) Usuário** — Perfil do demandante
4. **d) Finalidade** — Objetivo do conhecimento
5. **e) Prazo** — Deadline + urgência
6. **f) Aspectos Essenciais** — O que é crítico
7. **g) Aspectos Conhecidos** — O que já se sabe
8. **h) Aspectos a Conhecer** — O que falta descobrir
9. **i) PIRs & Coleta** — Requisitos + plano de coleta
10. **j) Medidas** — Segurança e extraordinárias

**Preview:** Exibe KPIs (Coverage, Linkage) e Gantt das tarefas.

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou pull request.

## 📄 Licença

Projeto ROC — Todos os direitos reservados.

## 📞 Suporte

Para dúvidas ou bugs, entre em contato com a equipe de desenvolvimento ROC.
