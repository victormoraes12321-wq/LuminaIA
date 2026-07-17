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
- Falha de login local apos autenticar: confirmar se frontend e API estao no mesmo host loopback. Se o navegador abriu `127.0.0.1:3000`, a API deve resolver para `127.0.0.1:8000`; se abriu `localhost:3000`, deve resolver para `localhost:8000`.
- Falha OpenAI: validar `OPENAI_API_KEY`, modelo e rede.
- Falha Oracle/PostgreSQL: validar credenciais, rede, pool e sync.
- Falha dashboard: validar payload runtime e console/frontend logs.
- Falha de acentos/textos quebrados: validar `frontend/lib/textEncoding.ts`, reparo em `useLuminaQuery`, `useDashboardRuntime`, `AuthContext`, `DataTable` e labels do `data_transformer`.
- Falha de continuidade no chat: validar envio de `session_id`, `history` e `parent_id` no payload de `/api/v1/query/`.

## Checklist De Perguntas Criticas

Em toda alteracao no orquestrador, metadata resolver, transformer ou frontend de chat, validar:

- Faturamento do mes.
- Faturamento do mes anterior.
- Venda por vendedor.
- Maior vendedor.
- Vendedor com maior desconto.
- Total de desconto e desconto medio.
- Ticket medio.
- Top/ranking de clientes sem retornar a loja interna.
- Pergunta de continuidade herdando o periodo anterior.
