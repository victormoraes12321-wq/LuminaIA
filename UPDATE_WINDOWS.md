# LuminaAI V2 — Guia de Atualização Nativa no Windows Server

Este documento descreve o procedimento seguro para atualizar uma instalação nativa existente do **LuminaAI** no Windows Server 2025 sem perda de dados ou indisponibilidade desnecessária.

---

## 1. Procedimento de Atualização

### Passo 1: Parar os Serviços
No diretório da aplicação:
```powershell
powershell -ExecutionPolicy Bypass -File stop-luminaai-windows.ps1
```

### Passo 2: Fazer Backup do Banco de Dados e Configurações
```powershell
# Backup do arquivo de configuracao
Copy-Item backend\.env backend\.env.backup

# Backup do PostgreSQL (usando pg_dump)
pg_dump -U lumina_preprod_user -h 127.0.0.1 -d lumina_preprod -F c -b -v -f "backup_pre_update_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
```

### Passo 3: Atualizar o Código-Fonte
Descompacte a nova versão sobrepondo os arquivos da aplicação (preservando `backend\.env` e `runtime-logs\`).

### Passo 4: Atualizar Dependências do Backend
```powershell
.\backend\.venv\Scripts\pip.exe install -r backend\requirements.txt
```

### Passo 5: Executar Migrações de Banco de Dados
```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\bootstrap_windows_preprod.py
```

### Passo 6: Recompilar o Frontend
```powershell
cd frontend
npm ci
npm run build
cd ..
```

### Passo 7: Reiniciar o LuminaAI
```powershell
powershell -ExecutionPolicy Bypass -File start-luminaai-windows.ps1
```

### Passo 8: Validar Status
```powershell
powershell -ExecutionPolicy Bypass -File status-luminaai-windows.ps1
```
