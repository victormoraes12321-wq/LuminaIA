# Guia de Implantação e Deploy — LuminaAI V2 RC4

Este documento detalha as estratégias oficiais de implantação do **LuminaAI V2 RC4**, com foco na arquitetura de contêineres Linux sob Windows Server / Hyper-V.

---

## 1. Topologia de Implantação

A arquitetura oficial de deploy do LuminaAI V2 é baseada em contêineres Docker orquestrados via Docker Compose, com terminação TLS e balanceamento de carga via Nginx:

```
┌─────────────────────────────────────────────────────────────┐
│ Servidor / VM de Pré-Produção / Produção                   │
│                                                             │
│  [ Porta 80 / 443 ]                                         │
│          │                                                  │
│          ▼                                                  │
│  ┌───────────────────────────────────────────┐              │
│  │ Nginx Reverse Proxy (lumina-nginx)        │              │
│  └───────┬───────────────────────────┬───────┘              │
│          │ /api/                     │ / (UI)               │
│          ▼                           ▼                      │
│  ┌────────────────────────┐  ┌───────────────────────────┐  │
│  │ Upstream Cluster       │  │ Frontend Next.js          │  │
│  │ ├─ lumina-backend-1    │  │ (lumina-frontend:3000)    │  │
│  │ └─ lumina-backend-2    │  └───────────────────────────┘  │
│  └───────┬────────────────┘                                 │
│          │ PostgreSQL asyncpg                               │
│          ▼                                                  │
│  ┌───────────────────────────────────────────┐              │
│  │ PostgreSQL 16 Dedicado                    │              │
│  └───────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Pacote de Deploy Imutável (`lumina-v2-rc4-deploy`)

A implantação em servidores não deve utilizar pastas de trabalho de desenvolvedores (*dirty worktree*). Utilize o pacote oficial gerado a partir da tag de release:

- **Arquivo:** `lumina-v2-rc4-deploy.tar.gz` (ou `.zip`)
- **Manifesto de Integridade:** `RELEASE_MANIFEST.txt`
- **Hash SHA-256:** `9fc0027aad9bb581a72459a030a2013dc6295a06f0c592d7780cfa14a844cf99`

---

## 3. Implantação Passo a Passo (Docker Compose)

### Passo 1: Transferência e Descompactação
```bash
mkdir -p /opt/luminaai
cd /opt/luminaai
tar -xzf lumina-v2-rc4-deploy.tar.gz
```

### Passo 2: Configuração de Segredos e Ambiente
```bash
cp .env.preprod.example .env.preprod
chmod 600 .env.preprod
# Editar .env.preprod com as chaves reais de staging/produção
```

### Passo 3: Inicialização dos Contêineres
```bash
# Para subir com PostgreSQL externo / gerenciado:
docker compose -f docker-compose.preprod.yml up -d --build

# Para subir com PostgreSQL em contêiner dedicado (primeira instalação):
docker compose --profile with-db -f docker-compose.preprod.yml up -d --build
```

---

## 4. Hardening e Segurança em Contêineres

Os contêineres do LuminaAI são configurados com as seguintes políticas de segurança estritas:
- **Usuário Não-Root:** Execução com UID `10001` e GID `10001` (`lumina:lumina`).
- **Sistema de Arquivos Read-Only:** `read_only: true` no Dockerfile e no compose.
- **Descarte de Privilégios:** `cap_drop: ALL` e `security_opt: no-new-privileges:true`.
- **Volumes Efêmeros Isolados:** Montagens `tmpfs` para `/tmp`, logs e diretórios de conversação.

---

## 5. Guias Operacionais Relacionados

- [Guia de Primeira Instalação (First Boot)](deploy/PREPROD_FIRST_BOOT.md)
- [Guia de Atualização de Versão (Update)](deploy/PREPROD_UPDATE.md)
- [Guia de Rollback de Emergência](deploy/PREPROD_ROLLBACK.md)
- [Modelo de Segurança e Ameaças](security.md)
- [Guia de Operação e Runbooks](operation.md)
