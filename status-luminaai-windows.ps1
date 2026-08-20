<#
.SYNOPSIS
    Verificador de Status do LuminaAI V2 RC4 no Windows Server 2025.
.DESCRIPTION
    Exibe o estado de execucao dos PIDs gravados, portas 8000/3002,
    conectividade do PostgreSQL e sondas de saude HTTP.
#>

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $RootDir) { $RootDir = (Get-Location).Path }

$LogsDir = Join-Path $RootDir "runtime-logs"
$PidFile = Join-Path $LogsDir "luminaai.pids.json"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LuminaAI V2 RC4 - Status do Sistema (Windows Server)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$backendPid = 0
$frontendPid = 0
$backendPort = 8000
$frontendPort = 3002
$startedAt = "N/A"

if (Test-Path $PidFile) {
    try {
        $pids = Get-Content $PidFile -Raw | ConvertFrom-Json
        $backendPid = $pids.backend_pid
        $frontendPid = $pids.frontend_pid
        $backendPort = if ($pids.backend_port) { $pids.backend_port } else { 8000 }
        $frontendPort = if ($pids.frontend_port) { $pids.frontend_port } else { 3002 }
        $startedAt = $pids.started_at
    } catch {}
}

# 1. Checar Processo Backend
$bProc = if ($backendPid -gt 0) { Get-Process -Id $backendPid -ErrorAction SilentlyContinue } else { $null }
$bStatus = if ($bProc) { "[EM EXECUCAO]" } else { "[PARADO]" }
$bColor = if ($bProc) { "Green" } else { "Red" }

# 2. Checar Processo Frontend
$fProc = if ($frontendPid -gt 0) { Get-Process -Id $frontendPid -ErrorAction SilentlyContinue } else { $null }
$fStatus = if ($fProc) { "[EM EXECUCAO]" } else { "[PARADO]" }
$fColor = if ($fProc) { "Green" } else { "Red" }

Write-Host "PROCESSOS:" -ForegroundColor Yellow
Write-Host "  Backend  (PID $backendPid) : $bStatus" -ForegroundColor $bColor
Write-Host "  Frontend (PID $frontendPid) : $fStatus" -ForegroundColor $fColor
Write-Host "  Iniciado em        : $startedAt" -ForegroundColor Gray
Write-Host ""

# 3. Checar Portas TCP
$bPortConn = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
$fPortConn = Get-NetTCPConnection -LocalPort $frontendPort -State Listen -ErrorAction SilentlyContinue

Write-Host "PORTAS DE REDE:" -ForegroundColor Yellow
if ($bPortConn) {
    Write-Host "  Porta $backendPort (Backend API)  : [ABERTA / ESCUTANDO] (Owner PID: $($bPortConn.OwningProcess | Select-Object -First 1))" -ForegroundColor Green
} else {
    Write-Host "  Porta $backendPort (Backend API)  : [FECHADA]" -ForegroundColor Red
}

if ($fPortConn) {
    Write-Host "  Porta $frontendPort (Frontend Web) : [ABERTA / ESCUTANDO] (Owner PID: $($fPortConn.OwningProcess | Select-Object -First 1))" -ForegroundColor Green
} else {
    Write-Host "  Porta $frontendPort (Frontend Web) : [FECHADA]" -ForegroundColor Red
}
Write-Host ""

# 4. Checar Conectividade PostgreSQL 5432
Write-Host "BANCO DE DADOS:" -ForegroundColor Yellow
$pgTest = Test-NetConnection -ComputerName "127.0.0.1" -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($pgTest) {
    Write-Host "  PostgreSQL (127.0.0.1:5432) : [CONECTADO / DISPONIVEL]" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL (127.0.0.1:5432) : [INACESSIVEL]" -ForegroundColor Red
}
Write-Host ""

# 5. Sondar Endpoints HTTP
Write-Host "SONDAS DE SAUDE HTTP:" -ForegroundColor Yellow
try {
    $hResp = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  /health       : 200 OK (Status: $($hResp.status), Versao: $($hResp.version))" -ForegroundColor Green
} catch {
    Write-Host "  /health       : [FALHA NA CONEXAO]" -ForegroundColor Red
}

try {
    $dResp = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/health/deep" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  /health/deep  : 200 OK (PostgreSQL: $($dResp.components.database.status))" -ForegroundColor Green
} catch {
    Write-Host "  /health/deep  : [INDISPONIVEL]" -ForegroundColor Yellow
}

try {
    $zResp = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/healthz" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  /healthz      : 200 OK" -ForegroundColor Green
} catch {
    Write-Host "  /healthz      : [INDISPONIVEL]" -ForegroundColor Yellow
}

Write-Host "======================================================================" -ForegroundColor Cyan
