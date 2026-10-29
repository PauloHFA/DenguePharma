param([int]$ApiPort = 18081, [int]$DashboardPort = 8501)
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$analyticsRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonExe = Join-Path $analyticsRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie analytics/.venv e instale o projeto antes de iniciar.' }
foreach ($servicePort in @($ApiPort, $DashboardPort)) {
    if (Get-NetTCPConnection -LocalPort $servicePort -State Listen -ErrorAction SilentlyContinue) {
        throw "Porta $servicePort ocupada. Nenhum processo foi interrompido; escolha outra porta ou use a instancia existente."
    }
}
$runtimePath = Join-Path $analyticsRoot 'target/runtime'
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
$env:ANALYTICS_DATA_DIR = Join-Path $analyticsRoot 'data'
$env:ANALYTICS_API_URL = "http://127.0.0.1:$ApiPort"
$dashboardFile = Join-Path $analyticsRoot 'src/denguepharma_analytics/dashboard.py'
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'denguepharma_analytics.cli', '--data-dir', "`"$env:ANALYTICS_DATA_DIR`"", 'serve', '--port', $ApiPort) -WorkingDirectory $workspaceRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'api.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'api.stderr.log') -PassThru
$dashboardProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'streamlit', 'run', "`"$dashboardFile`"", '--server.address', '127.0.0.1', '--server.port', $DashboardPort, '--server.headless', 'true', '--browser.gatherUsageStats', 'false') -WorkingDirectory $workspaceRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'streamlit.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'streamlit.stderr.log') -PassThru
@{api_pid=$apiProcess.Id; dashboard_pid=$dashboardProcess.Id; api_url=$env:ANALYTICS_API_URL; dashboard_url="http://127.0.0.1:$DashboardPort"} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $runtimePath 'processes.json')
Write-Output "API: http://127.0.0.1:$ApiPort ; dashboard: http://127.0.0.1:$DashboardPort"
