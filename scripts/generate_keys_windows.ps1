<#
.SYNOPSIS
    Gerador Seguro de Chaves Criptograficas para o LuminaAI V2 RC4 no Windows Server.
.DESCRIPTION
    Gera SECRET_KEY (Hex 32 bytes) e ENCRYPTION_KEY (Fernet Base64) em conformidade
    estrita com os requisitos de seguranca do LuminaAI config.py.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"

# Localiza o executavel Python (preferindo o venv)
$PythonExe = $null
if (Test-Path (Join-Path $BackendDir ".venv\Scripts\python.exe")) {
    $PythonExe = (Join-Path $BackendDir ".venv\Scripts\python.exe")
} elseif (Test-Path (Join-Path $BackendDir "venv\Scripts\python.exe")) {
    $PythonExe = (Join-Path $BackendDir "venv\Scripts\python.exe")
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} else {
    Write-Error "Python 3.12 nao foi encontrado no sistema ou no venv."
    exit 1
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LuminaAI V2 RC4 - Gerador de Chaves Criptograficas Seguras" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Gera SECRET_KEY (Hex 32 bytes -> 64 chars)
$SecretCmd = "import secrets; print(secrets.token_hex(32))"
$SecretKey = (& $PythonExe -c $SecretCmd).Trim()

# Gera ENCRYPTION_KEY (Fernet Base64)
$FernetCmd = "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$EncryptionKey = (& $PythonExe -c $FernetCmd).Trim()

if (-not $SecretKey -or -not $EncryptionKey) {
    Write-Error "Falha ao gerar chaves criptograficas. Verifique se o pacote 'cryptography' esta instalado."
    exit 1
}

Write-Host ""
Write-Host "Copie os valores abaixo para o arquivo backend/.env:" -ForegroundColor Yellow
Write-Host ""
Write-Host "SECRET_KEY=$SecretKey" -ForegroundColor Green
Write-Host "ENCRYPTION_KEY=$EncryptionKey" -ForegroundColor Green
Write-Host ""
Write-Host "Requisitos validados:" -ForegroundColor Gray
Write-Host "  [OK] SECRET_KEY: Hex criptografico ($($SecretKey.Length) caracteres, minimo 32)" -ForegroundColor Gray
Write-Host "  [OK] ENCRYPTION_KEY: Chave Fernet Base64 canonica (32 bytes url-safe)" -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
