<#
.SYNOPSIS
    Script assistido para vincular o repositório remoto do GitHub e realizar o push do LuminaAI V2 RC4.
#>
param (
    [Parameter(Mandatory = $false)]
    [string]$RemoteUrl,

    [Parameter(Mandatory = $false)]
    [string]$Branch = "main"
)

$GitExe = "C:\Program Files\Git\cmd\git.exe"
if (-not (Test-Path $GitExe)) {
    $GitExe = (Get-Command git -ErrorAction SilentlyContinue).Path
}

if (-not $GitExe) {
    Write-Error "Git nao encontrado no servidor. Instale o Git antes de continuar."
    exit 1
}

if (-not $RemoteUrl) {
    $RemoteUrl = Read-Host "Informe a URL do repositorio remoto no GitHub (ex: https://github.com/usuario/lumina-ai.git)"
}

if (-not $RemoteUrl) {
    Write-Error "URL do repositorio nao informada."
    exit 1
}

Write-Host "Configurando remote 'origin'..." -ForegroundColor Cyan
& $GitExe remote remove origin 2>$null
& $GitExe remote add origin $RemoteUrl

Write-Host "Renomeando branch local para $Branch..." -ForegroundColor Cyan
& $GitExe branch -M $Branch

Write-Host "Enviando arquivos para o GitHub ($Branch)..." -ForegroundColor Green
& $GitExe push -u origin $Branch

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Codigo enviado com sucesso para o GitHub!" -ForegroundColor Green
} else {
    Write-Warning "Falha no envio. Se o repositorio remoto ja tiver commits, tente usar --force ou sincronizar o historico."
}
