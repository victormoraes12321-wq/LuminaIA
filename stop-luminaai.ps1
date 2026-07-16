param(
  [int]$FrontendPort = 3000,
  [int]$BackendPort = 8000
)

$ErrorActionPreference = "SilentlyContinue"

foreach ($port in @($FrontendPort, $BackendPort)) {
  $owners = Get-NetTCPConnection -State Listen -LocalPort $port |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $owners) {
    if ($procId) {
      Stop-Process -Id $procId -Force
    }
  }
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"

$relatedProcesses = Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -and (
      ($_.CommandLine.Contains($BackendDir) -and ($_.CommandLine -match "uvicorn|main:app")) -or
      ($_.CommandLine.Contains($FrontendDir) -and ($_.CommandLine -match "next|npm|start-server"))
    )
  }

foreach ($process in $relatedProcesses) {
  Stop-Process -Id $process.ProcessId -Force
}

Start-Sleep -Seconds 2

$remaining = Get-NetTCPConnection -State Listen -LocalPort @($FrontendPort, $BackendPort) |
  Select-Object LocalAddress, LocalPort, OwningProcess

if ($remaining) {
  $remaining | ConvertTo-Json
} else {
  "PORTS_CLOSED"
}
