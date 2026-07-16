# Guia De Operacao

## Health Checks

- Backend: `GET /health`.
- Frontend container: health check em `/login` no Dockerfile.

## Rotina Operacional

1. Verificar status de containers/processos.
2. Verificar logs backend/frontend/nginx.
3. Validar conexao banco e credenciais externas.
4. Monitorar tempo de resposta e erros HTTP.
5. Acompanhar sync, scheduler e filas.
6. Revisar Trust/Health/Performance/Security Centers quando disponiveis.

## Logs

- Backend usa logging Python.
- Nginx registra access/error logs.
- Frontend usa logs do processo Next.

## Backup

Usar `scripts/backup-db.sh` como base e validar restore periodicamente.

## Incidentes

- Falha de login: validar JWT, cookies, SECRET_KEY e horario do servidor.
- Falha OpenAI: validar `OPENAI_API_KEY`, modelo e rede.
- Falha Oracle/PostgreSQL: validar credenciais, rede, pool e sync.
- Falha dashboard: validar payload runtime e console/frontend logs.
