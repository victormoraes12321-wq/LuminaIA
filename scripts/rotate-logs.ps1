<#
.SYNOPSIS
    Rotacao de Logs para o LuminaAI V2 RC4 no Windows Server
.DESCRIPTION
    Rotaciona logs de execucao arquivando logs antigos e remove arquivos com mais de 14 dias.
#>

param(
    [string]$LogsDir = "C:\LuminaAI\runtime-logs",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "SilentlyContinue"

if (-not (Test-Path $LogsDir)) {
    exit 0
}

$ArchiveDir = Join-Path $LogsDir "archive"
if (-not (Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
}

$today = Get-Date -Format "yyyyMMdd"
$cutoffDate = (Get-Date).AddDays(-$RetentionDays)

# 1. Rotaciona logs que excedem 25MB ou no inicio do dia
$logFiles = Get-ChildItem -Path $LogsDir -Filter "*.log" -File
foreach ($file in $logFiles) {
    if ($file.Length -gt 25MB) {
        $archiveName = "$($file.BaseName)_$($today)_$($file.Length).log"
        $archivePath = Join-Path $ArchiveDir $archiveName
        try {
            Copy-Item -Path $file.FullName -Destination $archivePath -Force
            Clear-Content -Path $file.FullName -Force
            Write-Host "[OK] Rotacionado $($file.Name) -> $archiveName"
        } catch {
            Write-Host "[WARN] Nao foi possivel rotacionar $($file.Name): $_"
        }
    }
}

# 2. Expurga arquivos no arquivo com mais de $RetentionDays
$archivedFiles = Get-ChildItem -Path $ArchiveDir -File
foreach ($oldFile in $archivedFiles) {
    if ($oldFile.LastWriteTime -lt $cutoffDate) {
        Remove-Item -Path $oldFile.FullName -Force
        Write-Host "[OK] Expurgo de log antigo: $($oldFile.Name)"
    }
}

Write-Host "Rotina de log rotation concluida com sucesso."
