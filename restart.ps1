# TradeDoctor 重启脚本（开发环境）
# 用法: .\restart.ps1
# 环境: Windows PowerShell / PowerShell 7

$ErrorActionPreference = "Stop"

$BACKEND_PORT = 8000
$FRONTEND_PORT = 5173
$ROOT = $PSScriptRoot

$PYTHON = "$ROOT\backend\.venv\Scripts\python.exe"
$LOG_DIR = "$ROOT\.tmp"
New-Item -Force -ItemType Directory $LOG_DIR | Out-Null

function ok($msg)   { Write-Host "  " -NoNewline; Write-Host "[ok]" -ForegroundColor Green -NoNewline; Write-Host " $msg" }
function fail($msg) { Write-Host "  " -NoNewline; Write-Host "[fail]" -ForegroundColor Red -NoNewline; Write-Host " $msg" }

Write-Host "=== 重启 TradeDoctor (开发环境) ==="

# 1. 释放端口
Write-Host "[1/3] 释放端口 ${BACKEND_PORT} ${FRONTEND_PORT} ..."
& $PYTHON -c @"
import subprocess
r = subprocess.run(['netstat','-ano'], capture_output=True, text=True)
for port in ['8000', '5173']:
    for line in r.stdout.split('\n'):
        if f':{port} ' in line and 'LISTENING' in line:
            pid = line.strip().split()[-1]
            subprocess.run(['taskkill','/F','/PID', pid], capture_output=True)
            print(f'  :{port} PID={pid} killed')
print('  done')
"@
Start-Sleep 1

# 2. 启动后端
Write-Host "[2/3] 启动后端 :${BACKEND_PORT} ..."
Push-Location "$ROOT\backend"
$backendJob = Start-Process -NoNewWindow -PassThru -FilePath $PYTHON `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","$BACKEND_PORT" `
    -RedirectStandardOutput "$LOG_DIR\backend.log" `
    -RedirectStandardError "$LOG_DIR\backend.log"
Pop-Location
ok "PID=$($backendJob.Id)  日志: $LOG_DIR\backend.log"

# 3. 启动前端
Write-Host "[3/3] 启动前端 :${FRONTEND_PORT} ..."
Push-Location "$ROOT\frontend"
$frontendJob = Start-Process -NoNewWindow -PassThru -FilePath "npm" `
    -ArgumentList "run","dev","--","--port","$FRONTEND_PORT" `
    -RedirectStandardOutput "$LOG_DIR\frontend.log" `
    -RedirectStandardError "$LOG_DIR\frontend.log"
Pop-Location
ok "PID=$($frontendJob.Id)  日志: $LOG_DIR\frontend.log"

# 4. 等后端就绪
Write-Host ""
Write-Host -NoNewline "  等待后端就绪"
$ready = $false
for ($i = 1; $i -le 20; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/api/health" -UseBasicParsing -TimeoutSec 1
        Write-Host ""
        ok "后端就绪"
        $ready = $true
        break
    } catch {
        Write-Host -NoNewline "."
        Start-Sleep 0.5
    }
}

if (-not $ready) {
    fail "后端未能在 10s 内启动，查看日志: $LOG_DIR\backend.log"
    exit 1
}

Write-Host ""
Write-Host "  http://localhost:${FRONTEND_PORT}  ← 前端"
Write-Host "  http://localhost:${BACKEND_PORT}/api/health  ← 后端健康检查"
Write-Host "  日志目录: $LOG_DIR"
Write-Host "=== 完成 ==="
