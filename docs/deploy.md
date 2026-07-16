# Guia De Deploy

## Opcoes

- Docker Compose com `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` e `nginx.conf`.
- Systemd via `scripts/setup-systemd.sh` quando adaptado ao servidor.

## Docker Compose

```bash
docker compose build
docker compose up -d
```

Observacao: esta validacao nao foi executada no ambiente de auditoria porque `docker` nao estava instalado.

## Variaveis

- Backend usa `backend/.env`.
- Frontend usa variaveis Next conforme `.env.local`/ambiente.
- Secrets produtivos nunca devem ser versionados.

## Nginx

`nginx.conf` faz reverse proxy para backend e frontend, redireciona HTTP para HTTPS e aplica headers de seguranca basicos.

## Rollback

- Manter backup do banco antes de deploy.
- Manter imagem/artefato anterior.
- Reverter variaveis de ambiente se necessario.
- Validar `/health` e login apos rollback.
