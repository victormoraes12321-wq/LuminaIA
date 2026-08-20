<#
.SYNOPSIS
    Configurador de Firewall do Windows para o LuminaAI V2 RC4.
.DESCRIPTION
    Cria regras de entrada no Windows Defender Firewall exclusivamente para as portas
    autorizadas do LuminaAI: TCP 3002 (Frontend Web) e TCP 8000 (Backend API).
    NUNCA altera regras de outros sistemas (como porta 3000 ou 5432).
#>

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LuminaAI V2 RC4 - Configurador de Regras de Firewall (Windows)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Verifica privilegios de Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERRO] Este script requer privilegios de Administrador." -ForegroundColor Red
    Write-Host "Abra o PowerShell como Administrador e execute novamente." -ForegroundColor Yellow
    exit 1
}

# 1. Regra para Frontend Web (Porta 3002)
$RuleNameFrontend = "LuminaAI - Frontend Web (TCP 3002)"
$existingFrontend = Get-NetFirewallRule -DisplayName $RuleNameFrontend -ErrorAction SilentlyContinue

if ($existingFrontend) {
    Write-Host "  [OK] Regra de Firewall '$RuleNameFrontend' ja existe." -ForegroundColor Green
} else {
    New-NetFirewallRule -DisplayName $RuleNameFrontend `
        -Direction Inbound `
        -LocalPort 3002 `
        -Protocol TCP `
        -Action Allow `
        -Description "Permite acesso web ao frontend Next.js do LuminaAI" | Out-Null
    Write-Host "  [OK] Regra '$RuleNameFrontend' criada com sucesso." -ForegroundColor Green
}

# 2. Regra para Backend API (Porta 8000)
$RuleNameBackend = "LuminaAI - Backend API (TCP 8000)"
$existingBackend = Get-NetFirewallRule -DisplayName $RuleNameBackend -ErrorAction SilentlyContinue

if ($existingBackend) {
    Write-Host "  [OK] Regra de Firewall '$RuleNameBackend' ja existe." -ForegroundColor Green
} else {
    New-NetFirewallRule -DisplayName $RuleNameBackend `
        -Direction Inbound `
        -LocalPort 8000 `
        -Protocol TCP `
        -Action Allow `
        -Description "Permite chamadas HTTP a API FastAPI do LuminaAI" | Out-Null
    Write-Host "  [OK] Regra '$RuleNameBackend' criada com sucesso." -ForegroundColor Green
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  [OK] Portas 3002 e 8000 configuradas com sucesso no Windows Firewall." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
