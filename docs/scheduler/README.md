# Scheduler E Sync Engine

## Objetivo

Executar sincronizacoes de dados em background, respeitando tenant, travas de concorrencia e configuracoes de origem/destino.

## Implementacao

- `backend/services/scheduler.py`: loop simples iniciado no lifespan FastAPI.
- `backend/services/sync_service.py`: sincronizacao por tenant.
- `backend/services/data_platform/sync_engine.py`: engine de sync com lock por tenant.
- `backend/services/data_platform/sync_scheduler.py`: orquestrador de sync e agenda.
- `backend/models/sync_queue.py`: fila/status de sync.

## Fluxo

```text
FastAPI startup -> start_scheduler
-> run_sync_task/sync orchestrator
-> tenant config -> Oracle/mock/PostgreSQL clone
-> Metadata Catalog/Health/History
```

## Limitacoes

- Sincronizacao real depende de credenciais Oracle/PostgreSQL e rede.
- Validacao de carga simultanea real deve ocorrer em homologacao/producao.
