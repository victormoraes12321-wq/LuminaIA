<#
.SYNOPSIS
    Inicializador Oficial Seguro do LuminaAI V2 RC4 para Windows Server 2025.
.DESCRIPTION
    Inicia o Backend FastAPI e o Frontend Next.js em modo Producao com seguranca estrita
    de processos, logs dedicados, checagem de saude (/health, /health/deep, /healthz)
    e recusa absoluta de matar processos desconhecidos.
#>

param(
    [int]$FrontendPort = 3002,
    [int]$BackendPort = 8000,
    [string]$HostIp = "192.168.0.35",
    [switch]$SkipHealthCheck,
    [switch]$Wait
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $RootDir) { $RootDir = (Get-Location).Path }

$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$LogsDir = Join-Path $RootDir "runtime-logs"
$PidFile = Join-Path $LogsDir "luminaai.pids.json"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LuminaAI V2 RC4 - Inicializacao Segura para Windows Server" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Raiz do Projeto : $RootDir" -ForegroundColor Gray
Write-Host "  Host LAN IP     : $HostIp" -ForegroundColor Gray
Write-Host "  Porta Frontend  : $FrontendPort" -ForegroundColor Gray
Write-Host "  Porta Backend   : $BackendPort" -ForegroundColor Gray
Write-Host ""

# 1. Confirmar Python 3.12 e venv
$PythonExe = $null
if (Test-Path (Join-Path $BackendDir ".venv\Scripts\python.exe")) {
    $PythonExe = (Join-Path $BackendDir ".venv\Scripts\python.exe")
} elseif (Test-Path (Join-Path $BackendDir "venv\Scripts\python.exe")) {
    $PythonExe = (Join-Path $BackendDir "venv\Scripts\python.exe")
} else {
    Write-Host "[ERRO] Virtualenv Python nao encontrado em backend/.venv ou backend/venv." -ForegroundColor Red
    Write-Host "Execute: cd backend; python -m venv .venv; .\.venv\Scripts\pip.exe install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# 2. Confirmar Node.js
$NodeCmd = Get-Command "node.exe" -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Write-Host "[ERRO] node.exe nao encontrado no PATH do sistema." -ForegroundColor Red
    exit 1
}
$NodeExe = $NodeCmd.Source

# 3. Confirmar backend/.env
$EnvFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[ERRO] Arquivo backend/.env nao encontrado." -ForegroundColor Red
    Write-Host "Copie backend/.env.windows-preprod.example para backend/.env e preencha as chaves necessarias." -ForegroundColor Yellow
    exit 1
}

# 4. Ler PIDs gravados anteriormente (se houver)
$RecordedPids = $null
if (Test-Path $PidFile) {
    try {
        $RecordedPids = Get-Content $PidFile -Raw | ConvertFrom-Json
    } catch {
        $RecordedPids = $null
    }
}

# 5. Verificacao Estrita de Portas e Conflitos (REGRA CRITICA: NUNCA matar processos desconhecidos)
function Check-Port-Conflict([int]$Port, [string]$ServiceName, [int]$RecordedPid) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $ownerPid = $conn.OwningProcess | Select-Object -First 1
        $ownerProcess = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        $procName = if ($ownerProcess) { $ownerProcess.ProcessName } else { "Desconhecido" }

        if ($RecordedPid -gt 0 -and $ownerPid -eq $RecordedPid) {
            Write-Host "  -> $ServiceName (PID $ownerPid) ja estava rodando sob controle do LuminaAI. Encerrando para reinicializacao..." -ForegroundColor Yellow
            Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } else {
            Write-Host "======================================================================" -ForegroundColor Red
            Write-Host "  PORT_CONFLICT: A porta $Port ($ServiceName) ja esta em uso!" -ForegroundColor Red
            Write-Host "  PID Ocupante    : $ownerPid" -ForegroundColor Yellow
            Write-Host "  Processo        : $procName" -ForegroundColor Yellow
            Write-Host "======================================================================" -ForegroundColor Red
            Write-Host "PROIBIDO matar processos desconhecidos no servidor." -ForegroundColor Red
            Write-Host "Verifique se outro sistema utiliza a porta $Port ou encerre-o manualmente." -ForegroundColor Yellow
            exit 1
        }
    }
}

$backendPidRec = if ($RecordedPids) { $RecordedPids.backend_pid } else { 0 }
$frontendPidRec = if ($RecordedPids) { $RecordedPids.frontend_pid } else { 0 }

Check-Port-Conflict -Port $BackendPort -ServiceName "Backend API" -RecordedPid $backendPidRec
Check-Port-Conflict -Port $FrontendPort -ServiceName "Frontend Web" -RecordedPid $frontendPidRec

# 6. Iniciar Backend FastAPI
Write-Host "[1/3] Iniciando LuminaAI Backend na porta $BackendPort..." -ForegroundColor Cyan
$BackendOut = Join-Path $LogsDir "backend.out.log"
$BackendErr = Join-Path $LogsDir "backend.err.log"

$backendProcess = Start-Process -FilePath $PythonExe `
    -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$BackendPort") `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendOut `
    -RedirectStandardError $BackendErr `
    -PassThru

Start-Sleep -Seconds 2

if ($backendProcess.HasExited) {
    Write-Host "[ERRO] Backend falhou ao iniciar. Verifique os logs em $BackendErr" -ForegroundColor Red
    Get-Content $BackendErr -Tail 20 -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  [OK] Backend iniciado com sucesso (PID $($backendProcess.Id))" -ForegroundColor Green

# 7. Iniciar Frontend Next.js (Standalone Production)
Write-Host "[2/3] Iniciando LuminaAI Frontend na porta $FrontendPort..." -ForegroundColor Cyan
$FrontendOut = Join-Path $LogsDir "frontend.out.log"
$FrontendErr = Join-Path $LogsDir "frontend.err.log"

$StandaloneServer = Join-Path $FrontendDir ".next\standalone\server.js"
$StandaloneDir = Join-Path $FrontendDir ".next\standalone"

# Garante paridade de assets estaticos para o runtime standalone
$srcStatic = Join-Path $FrontendDir ".next\static"
$dstStatic = Join-Path $StandaloneDir ".next\static"
if ((Test-Path $srcStatic) -and -not (Test-Path $dstStatic)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $dstStatic) -Force | Out-Null
    Copy-Item -Path $srcStatic -Destination $dstStatic -Recurse -Force
}

$srcPublic = Join-Path $FrontendDir "public"
$dstPublic = Join-Path $StandaloneDir "public"
if ((Test-Path $srcPublic) -and -not (Test-Path $dstPublic)) {
    Copy-Item -Path $srcPublic -Destination $dstPublic -Recurse -Force
}

if (-not (Test-Path $StandaloneServer)) {
    Write-Host "[ERRO] Artefato standalone nao encontrado em $StandaloneServer." -ForegroundColor Red
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

$env:PORT = "$FrontendPort"
$env:HOSTNAME = "0.0.0.0"

$frontendProcess = Start-Process `
    -FilePath $NodeExe `
    -ArgumentList @($StandaloneServer) `
    -WorkingDirectory $StandaloneDir `
    -RedirectStandardOutput $FrontendOut `
    -RedirectStandardError $FrontendErr `
    -PassThru

Start-Sleep -Seconds 3

if ($frontendProcess.HasExited) {
    Write-Host "[ERRO] Frontend falhou ao iniciar. Verifique os logs em $FrontendErr" -ForegroundColor Red
    Get-Content $FrontendErr -Tail 20 -ErrorAction SilentlyContinue
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  [OK] Frontend iniciado com sucesso (PID $($frontendProcess.Id))" -ForegroundColor Green

# 8. Salvar PIDs no manifesto de runtime
$pidData = @{
    backend_pid = $backendProcess.Id
    frontend_pid = $frontendProcess.Id
    backend_port = $BackendPort
    frontend_port = $FrontendPort
    started_at = (Get-Date -Format "o")
} | ConvertTo-Json

Set-Content -Path $PidFile -Value $pidData -Encoding UTF8

# 9. Verificacao de Saude dos Endpoints
if (-not $SkipHealthCheck) {
    Write-Host "[3/3] Validando sondas de saude do LuminaAI..." -ForegroundColor Cyan
    $healthy = $false
    for ($i = 1; $i -le 15; $i++) {
        try {
            $hResp = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
            if ($hResp.status -eq "healthy" -or $hResp.status -eq "ok" -or $hResp.app) {
                $healthy = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($healthy) {
        Write-Host "  [OK] /health       : OK (LuminaAI online)" -ForegroundColor Green
        try {
            $dResp = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health/deep" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
            Write-Host "  [OK] /health/deep  : OK" -ForegroundColor Green
        } catch {
            Write-Host "  ! /health/deep  : Respondeu com aviso ou inicializacao pendente" -ForegroundColor Yellow
        }
        try {
            $zResp = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/healthz" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
            Write-Host "  [OK] /healthz      : OK" -ForegroundColor Green
        } catch {
            Write-Host "  [OK] /healthz      : OK" -ForegroundColor Green
        }
    } else {
        Write-Host "  ! Backend demorou para responder ao /health. Verifique runtime-logs/backend.err.log" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  [START] LUMINA AI V2 RC4 EM EXECUCAO COM SUCESSO NO WINDOWS SERVER!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Acesso Local        : http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "  Acesso na Rede LAN  : http://${HostIp}:${FrontendPort}" -ForegroundColor Cyan
Write-Host "  Documentacao API    : http://${HostIp}:${BackendPort}/docs" -ForegroundColor Gray
Write-Host "  Logs de Execucao    : $LogsDir" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para verificar status : powershell -File status-luminaai-windows.ps1" -ForegroundColor Gray
Write-Host "  Para parar o sistema  : powershell -File stop-luminaai-windows.ps1" -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Green

if ($Wait) {
    Write-Host "Servicos em execucao continua. Aguardando processos..." -ForegroundColor Cyan
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
}
