#!/bin/bash

# ====================================================================
# LuminaAI — Script de Configuração systemd (Deploy Linux Nativo)
# ====================================================================
# Este script automatiza o registro do backend e frontend como serviços
# nativos no Linux, com auto-recuperação (restart on failure) e boot start.
# ====================================================================

# Impede a execução se não for root (necessário para mexer no systemd)
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, execute este script como root (sudo ./setup-systemd.sh)"
  exit 1
fi

# Diretório base (obrigatório atualizar com o caminho real no servidor)
INSTALL_DIR=$(pwd)
BACKEND_DIR="$INSTALL_DIR/backend"
FRONTEND_DIR="$INSTALL_DIR/frontend"
USER_EXEC=$SUDO_USER

echo "================================================================"
echo "⚙️ Configurando Serviços LuminaAI (systemd)..."
echo "Diretório de Instalação: $INSTALL_DIR"
echo "Usuário Executor: $USER_EXEC"
echo "================================================================"

# ── 1. Criar Serviço para o Backend (FastAPI + Gunicorn) ───────
echo "📦 Criando serviço para o backend (/etc/systemd/system/lumina-backend.service)..."

cat <<EOF > /etc/systemd/system/lumina-backend.service
[Unit]
Description=LuminaAI Backend (FastAPI API)
After=network.target postgresql.service

[Service]
User=$USER_EXEC
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BACKEND_DIR/.venv/bin/gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 127.0.0.1:8000
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=lumina-backend

[Install]
WantedBy=multi-user.target
EOF

# ── 2. Criar Serviço para o Frontend (Next.js) ──────────────────
echo "📦 Criando serviço para o frontend (/etc/systemd/system/lumina-frontend.service)..."

cat <<EOF > /etc/systemd/system/lumina-frontend.service
[Unit]
Description=LuminaAI Frontend (Next.js App)
After=network.target lumina-backend.service

[Service]
User=$USER_EXEC
WorkingDirectory=$FRONTEND_DIR
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=lumina-frontend

[Install]
WantedBy=multi-user.target
EOF

# ── 3. Registrar e Habilitar os Serviços no Boot ───────────────
echo "🔄 Recarregando daemons do systemd..."
systemctl daemon-reload

echo "⚡ Habilitando serviços na inicialização automática do servidor..."
systemctl enable lumina-backend
systemctl enable lumina-frontend

echo "▶️ Iniciando os serviços..."
systemctl start lumina-backend
systemctl start lumina-frontend

echo "================================================================"
echo "✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!"
echo "Os serviços agora rodarão em segundo plano permanentemente."
echo "Caso o servidor desligue ou reinicie, eles voltarão sozinhos."
echo "Se algum serviço cair devido a erros, o sistema o reiniciará."
echo "================================================================"
echo "Para verificar os status:"
echo "  systemctl status lumina-backend"
echo "  systemctl status lumina-frontend"
echo "Para ler os logs de erro:"
echo "  journalctl -u lumina-backend -n 50 -f"
echo "  journalctl -u lumina-frontend -n 50 -f"
echo "================================================================"
