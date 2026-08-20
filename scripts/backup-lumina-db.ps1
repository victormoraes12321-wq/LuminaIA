<#
.SYNOPSIS
    Rotina de Backup Diario Seguro para o LuminaAI (PostgreSQL) no Windows Server
.DESCRIPTION
    Executa dump logico no formato Custom (-Fc), calcula hash SHA-256 e valida integridade via pg_restore --list.
#>

param(
    [string]$BackupDir = "C:\Backups\LuminaAI",
    [string]$Database = "lumina_preprod",
    [string]$User = "lumina_preprod_user",
    [string]$DbHost = "127.0.0.1",
    [int]$Port = 5432,
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

# 1. Garante existencia do diretorio de destino
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# 2. Localiza pg_dump e pg_restore
$pgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
$pgRestore = "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"

if (-not (Test-Path $pgDump)) {
    Write-Host "[ERRO] pg_dump nao encontrado em $pgDump" -ForegroundColor Red
    exit 1
}

# 3. Le credenciais de forma segura do .env sem expor em logs
$envFile = "C:\LuminaAI\backend\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*POSTGRES_PASSWORD\s*=\s*(.+)$') {
            $env:PGPASSWORD = $matches[1].Trim('"').Trim("'")
        }
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dumpFile = Join-Path $BackupDir "${Database}_${timestamp}.dump"
$shaFile = "${dumpFile}.sha256"

Write-Host "Iniciando backup logico de '$Database' para '$dumpFile'..."

try {
    # 4. Executa pg_dump
    & $pgDump -h $DbHost -p $Port -U $User -d $Database -Fc -f $dumpFile
    
    if (-not (Test-Path $dumpFile)) {
        throw "Arquivo de dump nao foi criado."
    }

    $fileSize = (Get-Item $dumpFile).Length
    if ($fileSize -eq 0) {
        throw "Arquivo de dump gerado com 0 bytes."
    }
    Write-Host "  [OK] Dump gerado com sucesso ($fileSize bytes)." -ForegroundColor Green

    # 5. Calcula SHA-256
    $hash = (Get-FileHash -Path $dumpFile -Algorithm SHA256).Hash
    "$hash  $(Split-Path -Leaf $dumpFile)" | Out-File -FilePath $shaFile -Encoding ASCII
    Write-Host "  [OK] SHA-256 gerado: $hash" -ForegroundColor Green

    # 6. Valida integridade do arquivo com pg_restore --list
    $catalogList = & $pgRestore --list $dumpFile
    if ($LASTEXITCODE -ne 0 -or $catalogList.Count -eq 0) {
        throw "Validacao com pg_restore --list falhou."
    }
    Write-Host "  [OK] pg_restore --list validou integridade do archive ($($catalogList.Count) entradas no catalogo)." -ForegroundColor Green

    # 7. Expurga backups com mais de $RetentionDays
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -Path $BackupDir -File | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
        Remove-Item -Path $_.FullName -Force
        Write-Host "  [OK] Expurgo de backup antigo: $($_.Name)" -ForegroundColor Yellow
    }

    Write-Host "[OK] Backup do banco de dados '$Database' concluido com sucesso." -ForegroundColor Green
} finally {
    $env:PGPASSWORD = $null
}
