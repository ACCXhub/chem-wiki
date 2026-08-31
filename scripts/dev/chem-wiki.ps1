[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [ValidateSet('Start', 'Stop')]
  [string]$Action
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BackendRoot = Join-Path $RepoRoot 'backend'
$FrontendRoot = Join-Path $RepoRoot 'frontend'
$Python = Join-Path $BackendRoot '.venv\Scripts\python.exe'
$ViteScript = Join-Path $FrontendRoot 'node_modules\vite\bin\vite.js'
$RuntimeRoot = Join-Path $RepoRoot '.chem-wiki-dev'
$StatePath = Join-Path $RuntimeRoot 'services.json'
$BackendLog = Join-Path $RuntimeRoot 'backend.log'
$BackendErrorLog = Join-Path $RuntimeRoot 'backend-error.log'
$FrontendLog = Join-Path $RuntimeRoot 'frontend.log'
$FrontendErrorLog = Join-Path $RuntimeRoot 'frontend-error.log'
$BackendUrl = 'http://127.0.0.1:8000/health'
$FrontendUrl = 'http://127.0.0.1:5173/'

function Write-Status([string]$Message) {
  Write-Host $Message -ForegroundColor Green
}

function Assert-Command([string]$Name, [string]$SetupMessage) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name 不可用。$SetupMessage"
  }
}

function Assert-Path([string]$Path, [string]$SetupMessage) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "$Path 不存在。$SetupMessage"
  }
}

function Invoke-Native([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage) {
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$FailureMessage（退出码 $LASTEXITCODE）"
  }
}

function Test-DockerReady {
  $previousErrorAction = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & docker info *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $previousErrorAction
  }
}

function Ensure-DockerReady {
  if (Test-DockerReady) { return }

  $started = $false
  $previousErrorAction = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & docker desktop start --detach *> $null
    $started = $LASTEXITCODE -eq 0
  } catch {
    $started = $false
  } finally {
    $ErrorActionPreference = $previousErrorAction
  }

  if (-not $started) {
    $dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
      throw 'Docker Desktop 引擎未运行，且未找到 Docker Desktop.exe。请安装并启动 Docker Desktop。'
    }
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
  }
  Write-Host '正在启动 Docker Desktop…'
  foreach ($attempt in 1..60) {
    Start-Sleep -Seconds 1
    if (Test-DockerReady) { return }
  }
  throw 'Docker Desktop 在 60 秒内未就绪。请打开 Docker Desktop 检查其状态后重试。'
}

function Get-ListenerProcess([int]$Port) {
  $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if (-not $listener) { return $null }
  return Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
}

function Test-Endpoint([string]$Url) {
  try {
    return (Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -eq 200
  } catch {
    return $false
  }
}

function Wait-ForEndpoint([string]$Url, [string]$Name, [string[]]$LogPaths) {
  foreach ($attempt in 1..30) {
    if (Test-Endpoint $Url) { return }
    Start-Sleep -Seconds 1
  }
  $recentLogs = $LogPaths | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
    "`n$($_)：`n$(Get-Content -LiteralPath $_ -Tail 30 | Out-String)"
  }
  $logHint = if ($recentLogs) { "`n最近日志：$($recentLogs -join '')" } else { '' }
  throw "$Name 未能在 30 秒内就绪。$logHint"
}

function Get-ProcessId($Process) {
  if ($Process.PSObject.Properties.Name -contains 'ProcessId') { return $Process.ProcessId }
  return $Process.Id
}

function Get-ChemWikiService([ValidateSet('Backend', 'Frontend')] [string]$Name) {
  $port = if ($Name -eq 'Backend') { 8000 } else { 5173 }
  $process = Get-ListenerProcess $port
  if (-not $process) { return $null }

  $commandLine = $process.CommandLine
  $isExpected = if ($Name -eq 'Backend') {
    $commandLine.Contains($Python) -and
      $commandLine.Contains('chem_wiki.main:app') -and
      $commandLine.Contains((Join-Path $BackendRoot 'src'))
  } else {
    $commandLine.Contains($ViteScript)
  }
  if ($isExpected) { return $process }
  throw "端口 $port 已被非 Chem Wiki 开发服务占用（PID $($process.ProcessId)）。请先释放该端口。"
}

function Write-ServiceState($BackendProcess, $FrontendProcess) {
  New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
  [pscustomobject]@{
    backendPid = Get-ProcessId $BackendProcess
    frontendPid = Get-ProcessId $FrontendProcess
  } | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8
}

function Start-ChemWiki {
  $envPath = Join-Path $RepoRoot '.env'
  $envExamplePath = Join-Path $RepoRoot '.env.example'
  if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Host '已从 .env.example 创建 .env。' -ForegroundColor Yellow
  }

  Assert-Command 'docker' '请安装并启动 Docker Desktop。'
  Assert-Command 'node' '请安装项目要求的 Node.js 运行时。'
  Assert-Path $Python '请在 backend 目录执行 uv sync --locked --dev。'
  Assert-Path $ViteScript '请在 frontend 目录执行 npm ci。'

  Invoke-Native 'docker' @('compose', '--project-directory', $RepoRoot, 'version') 'Docker Compose 不可用'
  Ensure-DockerReady
  Invoke-Native 'docker' @('compose', '--project-directory', $RepoRoot, 'up', '-d', '--wait', 'postgres') 'PostgreSQL 未能启动'
  Write-Status '数据库已就绪'

  $databaseUrlLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
  if (-not $databaseUrlLine) { throw '.env 缺少 DATABASE_URL。请从 .env.example 补充后重试。' }
  $env:DATABASE_URL = ($databaseUrlLine -replace '^\s*DATABASE_URL\s*=\s*', '').Trim().Trim('"')
  $backendSource = Join-Path $BackendRoot 'src'
  $env:PYTHONPATH = if ($env:PYTHONPATH) {
    "$backendSource$([IO.Path]::PathSeparator)$env:PYTHONPATH"
  } else {
    $backendSource
  }

  Invoke-Native $Python @('-m', 'alembic', '-c', (Join-Path $BackendRoot 'alembic.ini'), 'upgrade', 'head') '数据库迁移失败'

  if (-not $env:KNOWLEDGE_CATALOG_SOURCE) {
    $siblingCatalog = Join-Path (Split-Path $RepoRoot -Parent) 'chem-knowledge-data'
    if (Test-Path -LiteralPath $siblingCatalog) {
      $env:KNOWLEDGE_CATALOG_SOURCE = $siblingCatalog
    }
  }
  Push-Location $BackendRoot
  try {
    Invoke-Native $Python @('-m', 'chem_wiki.modules.knowledge_catalog.cli', '--if-missing') '目录数据初始化失败'
  } finally {
    Pop-Location
  }
  Write-Status '目录数据已就绪'

  New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
  $backendProcess = Get-ChemWikiService 'Backend'
  if ($backendProcess) {
    if (-not (Test-Endpoint $BackendUrl)) { throw '检测到 Chem Wiki 后端进程，但健康检查失败。请先运行 stop-chem-wiki.cmd。' }
  } else {
    $backendProcess = Start-Process -FilePath $Python -ArgumentList @('-m', 'uvicorn', 'chem_wiki.main:app', '--app-dir', (Join-Path $BackendRoot 'src'), '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $BackendRoot -WindowStyle Hidden -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrorLog -PassThru
    Wait-ForEndpoint $BackendUrl '后端' @($BackendLog, $BackendErrorLog)
  }
  Write-Status '后端已就绪'

  $frontendProcess = Get-ChemWikiService 'Frontend'
  if ($frontendProcess) {
    if (-not (Test-Endpoint $FrontendUrl)) { throw '检测到 Chem Wiki 前端进程，但页面不可访问。请先运行 stop-chem-wiki.cmd。' }
  } else {
    $node = (Get-Command 'node').Source
    $frontendProcess = Start-Process -FilePath $node -ArgumentList @($ViteScript, '--host', '127.0.0.1', '--port', '5173', '--strictPort') -WorkingDirectory $FrontendRoot -WindowStyle Hidden -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrorLog -PassThru
    Wait-ForEndpoint $FrontendUrl '前端' @($FrontendLog, $FrontendErrorLog)
  }
  Write-ServiceState $backendProcess $frontendProcess
  Write-Status '前端已就绪'

  Start-Process $FrontendUrl
  Write-Status 'Chem Wiki 已启动'
}

function Stop-ChemWiki {
  $services = @()
  foreach ($name in @('Backend', 'Frontend')) {
    try {
      $process = Get-ChemWikiService $name
      if ($process) { $services += $process }
    } catch {
      Write-Host $_.Exception.Message -ForegroundColor Yellow
    }
  }

  foreach ($process in ($services | Sort-Object ProcessId -Unique)) {
    Stop-Process -Id $process.ProcessId -ErrorAction Stop
    Write-Host "已停止 Chem Wiki 进程（PID $($process.ProcessId)）。"
  }
  if (Test-Path -LiteralPath $StatePath) { Remove-Item -LiteralPath $StatePath -Force }
  if (-not $services) { Write-Host '未发现正在运行的 Chem Wiki 前后端服务。' }
}

try {
  if ($Action -eq 'Start') { Start-ChemWiki } else { Stop-ChemWiki }
} catch {
  Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
