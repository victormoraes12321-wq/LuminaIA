# Guia de Instalação — LuminaAI V2 RC4

Este documento descreve os pré-requisitos e procedimentos completos para instalação do **LuminaAI V2 RC4** em ambientes de desenvolvimento local e servidores corporativos.

---

## 1. Pré-Requisitos do Sistema

- **Python:** 3.12.x (com pip e venv)
- **Node.js:** 20.x LTS ou 24.x LTS (com npm 10+)
- **Banco de Dados:** PostgreSQL 16+ (com suporte a conexões assíncronas via `asyncpg`)
- **Provedor de IA:** Chave de API OpenAI (`gpt-4o-mini` autorizado)
- **Opcional (Containerização):** Docker Engine 26+ e Docker Compose v2

---

## 2. Instalação do Backend (FastAPI)

```powershell
# 1. Navegar até a pasta do backend
cd backend

# 2. Criar e ativar ambiente virtual Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # No Linux: source .venv/bin/activate

# 3. Instalar dependências auditadas
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
copy .env.example .env         # No Linux: cp .env.example .env
```

### Configurações Obrigatórias no `.env`:
- `DATABASE_URL`: String de conexão assíncrona PostgreSQL (`postgresql+asyncpg://usuario:senha@host:5432/lumina_db`).
- `SECRET_KEY`: Chave secreta hexadecimal de 64 caracteres para assinatura de tokens JWT (`openssl rand -hex 32`).
- `ENCRYPTION_KEY`: Chave Fernet de 32 bytes em base64 (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- `OPENAI_API_KEY`: Credencial válida do provedor OpenAI.

---

## 3. Inicialização e Migrações do Banco de Dados

O banco de dados pode ser inicializado através de:
```powershell
# Inicializar schema base via script SQL
psql -U postgres -d lumina_db -f backend/database/init.sql

# Ou via inicialização assíncrona SQLAlchemy (main.py executa create_all)
.\.venv\Scripts\python.exe -c "
import asyncio
from database import engine, Base
import models
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
print('Schema inicializado com sucesso!')
"
```

---

## 4. Instalação do Frontend (Next.js 16 / React 19)

```powershell
# 1. Navegar até a pasta do frontend
cd frontend

# 2. Instalar dependências limpas do lockfile
npm ci

# 3. Configurar variáveis de ambiente do frontend
copy .env.example .env.local   # No Linux: cp .env.example .env.local

# 4. Iniciar em modo de desenvolvimento
npm run dev -- --port 3002
```

---

## 5. Validação da Instalação (Health Check)

- **Backend Liveness:** `curl -s http://127.0.0.1:8000/health` (esperado: `HTTP 200 {"status": "healthy"}`)
- **Backend Readiness:** `curl -s http://127.0.0.1:8000/health/deep` (esperado: `HTTP 200` com relatório de componentes)
- **Frontend Health:** `curl -s http://127.0.0.1:3002/healthz` (esperado: `HTTP 200 {"status": "healthy"}`)
- **Acesso Web:** Abrir `http://localhost:3002` no navegador e realizar login corporativo.
