<#
.SYNOPSIS
    Parada Segura do LuminaAI V2 RC4 no Windows Server 2025.
.DESCRIPTION
    Encerra SOMENTE os processos gravados pelo start-luminaai-windows.ps1.
    NUNCA seleciona processos cegamente por porta.
#>

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $RootDir) { $RootDir = (Get-Location).Path }

$LogsDir = Join-Path $RootDir "runtime-logs"
$PidFile = Join-Path $LogsDir "luminaai.pids.json"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LuminaAI V2 RC4 - Parada Segura de Processos" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $PidFile)) {
    Write-Host "[INFO] Nenhum arquivo de PIDs ativo encontrado em $PidFile." -ForegroundColor Yellow
    Write-Host "O LuminaAI pode ja estar parado." -ForegroundColor Gray
    exit 0
}

try {
    $pids = Get-Content $PidFile -Raw | ConvertFrom-Json
} catch {
    Write-Host "[ERRO] Falha ao ler $PidFile. Removendo arquivo corrompido." -ForegroundColor Red
    Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

$backendPid = $pids.backend_pid
$frontendPid = $pids.frontend_pid

function Stop-Specific-Process([int]$PidToStop, [string]$ServiceName) {
    if ($PidToStop -gt 0) {
        $proc = Get-Process -Id $PidToStop -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  -> Encerrando $ServiceName (PID $PidToStop, Processo: $($proc.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $PidToStop -Force -ErrorAction SilentlyContinue
            Write-Host "  [OK] $ServiceName encerrado com sucesso." -ForegroundColor Green
        } else {
            Write-Host "  [INFO] $ServiceName (PID $PidToStop) ja nao estava em execucao." -ForegroundColor Gray
        }
    }
}

Stop-Specific-Process -PidToStop $frontendPid -ServiceName "Frontend Next.js"
Stop-Specific-Process -PidToStop $backendPid -ServiceName "Backend FastAPI"

Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  [OK] LuminaAI parado com seguranca (nenhum outro sistema afetado)." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
