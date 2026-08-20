# LuminaAI V2 — Guia de Rollback Nativo no Windows Server

Este documento descreve o procedimento operacional para reverter o **LuminaAI** para a versão anterior ou restaurar o estado estável do banco de dados no Windows Server 2025.

---

## 1. Procedimento de Rollback Rápido

### Passo 1: Parar o Sistema
```powershell
powershell -ExecutionPolicy Bypass -File stop-luminaai-windows.ps1
```

### Passo 2: Restaurar o Backup do Banco de Dados
Caso a atualização tenha envolvido mudanças de banco de dados:
```powershell
# Restaurar via pg_restore
pg_restore -U lumina_preprod_user -h 127.0.0.1 -d lumina_preprod --clean --if-exists -v "backup_pre_update_<TIMESTAMP>.dump"
```

### Passo 3: Restaurar os Arquivos da Versão Anterior
Restaure os arquivos da versão estável anterior (ou o arquivo zip da release estável).

### Passo 4: Recompilar o Frontend
```powershell
cd frontend
npm ci
npm run build
cd ..
```

### Passo 5: Reiniciar o Sistema
```powershell
powershell -ExecutionPolicy Bypass -File start-luminaai-windows.ps1
```

### Passo 6: Validar Conectividade
```powershell
powershell -ExecutionPolicy Bypass -File status-luminaai-windows.ps1
```
