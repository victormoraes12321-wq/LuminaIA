# Guia De Instalacao

## Pre-requisitos

- Python 3.12+
- Node.js 20+
- npm
- PostgreSQL acessivel
- Credenciais OpenAI
- Opcional: Oracle ou modo mock
- Opcional para deploy: Docker e Docker Compose

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Configurar `.env` com `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, `OPENAI_API_KEY` e demais variaveis.

## Banco

Executar `backend/database/init.sql` no PostgreSQL inicial ou usar scripts/migracoes conforme ambiente.

## Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Em ambiente local, use o mesmo host no navegador e na API. O frontend ajusta automaticamente `NEXT_PUBLIC_API_URL` quando o acesso e loopback, preservando `localhost` ou `127.0.0.1` para manter o cookie HttpOnly de sessao.

## Validacao Inicial

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run lint
npm run build
```

Para teste funcional rapido, abrir `/login`, autenticar, acessar `/dashboard` e perguntar `Faturamento e ticket medio em 06/2026`. A resposta deve renderizar sem mojibake e com labels humanizados.
