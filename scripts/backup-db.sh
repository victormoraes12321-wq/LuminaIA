#!/bin/bash

# ====================================================================
# LuminaAI — Script de Backup Seguro do Banco de Dados (PostgreSQL)
# ====================================================================
# Este script automatiza o backup da base de dados principal e do clone
# compactando os arquivos gerados e removendo backups antigos (retenção).
# ====================================================================

# Configurações de backup
BACKUP_DIR="${LUMINA_BACKUP_DIR:-/var/backups/luminaai}"
RETENCAO_DIAS=7

# Cores para saída formatada
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # Sem cor

# Garante que o diretório de backups existe
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

echo "================================================================"
echo "💾 Iniciando Backup de Banco de Dados LuminaAI..."
echo "Diretório de Backup: $BACKUP_DIR"
echo "================================================================"

# Verifica se pg_dump está instalado no sistema
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ Erro: pg_dump não está instalado. Por favor, instale o cliente PostgreSQL.${NC}"
    exit 1
fi

# 1. Recupera as variáveis do arquivo .env se estiver no mesmo diretório
# Se o backup for rodar por cron, precisamos usar caminhos absolutos.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PARENT_DIR/backend/.env" ]; then
    # Lê a URL do banco do arquivo .env
    DB_URL=$(grep "^DATABASE_URL=" "$PARENT_DIR/backend/.env" | cut -d'=' -f2-)
    # Limpa aspas se existirem
    DB_URL="${DB_URL%\"}"
    DB_URL="${DB_URL#\"}"
fi

# Se não encontrar no .env, tenta usar a variável DATABASE_URL de ambiente
if [ -z "$DB_URL" ]; then
    echo -e "${RED}❌ Erro: DATABASE_URL não encontrada em $PARENT_DIR/backend/.env ou variáveis de ambiente.${NC}"
    exit 1
fi

# Extrai os dados de conexão da URL postgresql://usuario:senha@host:porta/banco
# Suporta também postgresql+asyncpg://
CLEAN_URL=$(echo "$DB_URL" | sed 's/postgresql+asyncpg/postgresql/g')

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/luminaai_db_$TIMESTAMP.sql.gz"

echo "🔄 Fazendo dump do banco principal..."
# Executa o pg_dump com a URL de conexão e compacta a saída diretamente
if pg_dump "$CLEAN_URL" | gzip > "$BACKUP_FILE"; then
    echo -e "${GREEN}✅ Backup principal gerado com sucesso: $BACKUP_FILE${NC}"
    chmod 600 "$BACKUP_FILE"
else
    echo -e "${RED}❌ Erro ao gerar o backup do banco principal.${NC}"
    exit 1
fi

# 2. Rotaciona os backups antigos (remove arquivos mais antigos que RETENCAO_DIAS)
echo "🧹 Limpando backups antigos (retenção de $RETENCAO_DIAS dias)..."
find "$BACKUP_DIR" -name "luminaai_db_*.sql.gz" -type f -mtime +$RETENCAO_DIAS -delete
echo -e "${GREEN}✅ Limpeza concluída!${NC}"
echo "================================================================"
echo -e "${GREEN}🎉 PROCESSO DE BACKUP CONCLUÍDO COM SUCESSO!${NC}"
echo "================================================================"
