# Guia De Operacao

## Health Checks

- Backend: `GET /health`.
- Backend profundo: `GET /health/deep` valida API, PostgreSQL e status de IA/invocacao para diagnostico de queda ou degradacao.
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

- Dados desatualizados: conferir `data_status.synced_at`, `data_status.freshness` e `sync_config.last_sync`; a consulta continua usando somente o PostgreSQL.
- Divergencia matematica: conferir `validation_summary`; no perfil ADMIN, abrir `admin_diagnostics.validation` e o trace da resposta.
- Reconciliacao diaria: consultar `tenant.sync_config.last_reconciliation` e os eventos `ERP_RECONCILIATION` em `data_platform_history`.
- Rastreabilidade: usar `Ver documentos`; o detalhamento e lido da `vw_vendas_lm` sincronizada no PostgreSQL.

- Falha de login: validar JWT, cookies, SECRET_KEY e horario do servidor.
- Falha de login local apos autenticar: confirmar se frontend e API estao no mesmo host loopback. Se o navegador abriu `127.0.0.1:3000`, a API deve resolver para `127.0.0.1:8000`; se abriu `localhost:3000`, deve resolver para `localhost:8000`.
- Falha OpenAI: validar `OPENAI_API_KEY`, modelo e rede.
- Falha Oracle/PostgreSQL: validar credenciais, rede, pool e sync.
- Falha dashboard: validar payload runtime e console/frontend logs.
- Falha persistente apos longo tempo aberto: chamar `GET /health/deep`, conferir status de PostgreSQL/pool e reiniciar processo apenas depois de registrar logs.
- Falha em preferencias do popup de dashboard: validar `GET/PUT /api/v1/dashboard-preferences/default`, token JWT e tabela `dashboard_preferences`.
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

Comando oficial de regressao pesada para perguntas criticas:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_core_sales_redteam.py --json-report reports\core_sales_redteam_2026-07-20.json
```

Comando oficial para bater os relatorios criticos do clone contra o ERP Oracle:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_erp_reconciliation.py --period 2026-06 --period 2026-07 --json-report reports\erp_reconciliation_2026-07-20.json
```

Se o Oracle estiver fora da rede/VPN, o relatorio fica com `overall_status=needs_erp_connection` e registra o erro seguro de conexao. Para obrigar falha quando o ERP nao estiver acessivel, adicionar `--require-oracle`; para falhar apenas em divergencia numerica, adicionar `--fail-on-mismatch`.

Quando uma divergencia indicar clone defasado no dia corrente, ressincronizar a view LM com staging:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_lm_view_resync.py --view VW_VENDAS_LM --full
.\.venv\Scripts\python.exe scripts\run_lm_view_resync.py --view VW_VENDAS_LM
```

A segunda chamada usa incremental com janela de sobreposicao por `dtemissao_`, capturando vendas tardias do dia atual sem recarregar toda a base.

Comando oficial para mapear fontes candidatas de lucro e vendas ainda nao faturadas:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_financial_source_discovery.py --json-report reports\financial_source_discovery_2026-07-20.json
```

Lucro bruto/liquido so deve ser ativado depois de fonte com receita, custo/CMV, impostos/despesas ou coluna explicita homologada. Vendas ainda nao faturadas exigem fonte de pedido/carteira/orcamento com status operacional de faturamento, valor, data, filial e cancelamento quando existir.
