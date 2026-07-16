param(
  [int]$FrontendPort = 3000,
  [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogDir = Join-Path $Root "runtime-logs"

if (!(Test-Path $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir | Out-Null
}

foreach ($port in @($FrontendPort, $BackendPort)) {
  $owners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $owners) {
    if ($procId) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
  }
}

$relatedProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object {
    $_.CommandLine -and (
      ($_.CommandLine.Contains($BackendDir) -and ($_.CommandLine -match "uvicorn|main:app")) -or
      ($_.CommandLine.Contains($FrontendDir) -and ($_.CommandLine -match "next|npm|start-server"))
    )
  }

foreach ($process in $relatedProcesses) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$NextCache = Join-Path $FrontendDir ".next"
if (Test-Path $NextCache) {
  $ResolvedNextCache = (Resolve-Path $NextCache).Path
  if ($ResolvedNextCache.StartsWith($FrontendDir)) {
    Remove-Item -LiteralPath $ResolvedNextCache -Recurse -Force
  }
}

$PythonExe = "python"
if (Test-Path (Join-Path $BackendDir "venv\Scripts\python.exe")) {
  $PythonExe = (Resolve-Path (Join-Path $BackendDir "venv\Scripts\python.exe")).Path
} elseif (Test-Path (Join-Path $BackendDir ".venv\Scripts\python.exe")) {
  $PythonExe = (Resolve-Path (Join-Path $BackendDir ".venv\Scripts\python.exe")).Path
}

$BackendOut = Join-Path $LogDir "backend-network.out.log"
$BackendErr = Join-Path $LogDir "backend-network.err.log"
$FrontendOut = Join-Path $LogDir "frontend-network.out.log"
$FrontendErr = Join-Path $LogDir "frontend-network.err.log"

$backend = Start-Process -FilePath $PythonExe `
  -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$BackendPort") `
  -WorkingDirectory $BackendDir `
  -RedirectStandardOutput $BackendOut `
  -RedirectStandardError $BackendErr `
  -WindowStyle Hidden `
  -PassThru

$frontend = Start-Process -FilePath "npm.cmd" `
  -ArgumentList @("run", "dev") `
  -WorkingDirectory $FrontendDir `
  -RedirectStandardOutput $FrontendOut `
  -RedirectStandardError $FrontendErr `
  -WindowStyle Hidden `
  -PassThru

Start-Sleep -Seconds 10

$ip = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
  Select-Object -First 1 -ExpandProperty IPAddress

$checks = [ordered]@{}
foreach ($url in @(
  "http://127.0.0.1:$BackendPort/health",
  "http://127.0.0.1:$FrontendPort/login",
  "http://$ip`:$BackendPort/health",
  "http://$ip`:$FrontendPort/login"
)) {
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 0
    $checks[$url] = [int]$response.StatusCode
  } catch {
    $checks[$url] = $_.Exception.Message
  }
}

[pscustomobject]@{
  backend_pid = $backend.Id
  frontend_pid = $frontend.Id
  local_frontend = "http://localhost:$FrontendPort/login"
  network_frontend = "http://$ip`:$FrontendPort/login"
  local_backend_health = "http://127.0.0.1:$BackendPort/health"
  network_backend_health = "http://$ip`:$BackendPort/health"
  checks = $checks
} | ConvertTo-Json -Depth 4
