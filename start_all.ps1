# Script ejecutor completo (API + Bot) para PowerShell sin bloqueos de Ctrl+C
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   BOT-MT5 - Arranque completo (PS)" -ForegroundColor Cyan
Write-Host "   Bot Python + API movil" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ROOT = $PSScriptRoot
$API_DIR = Join-Path $ROOT "mobile-app\artifacts\api-server"

# Compilar API
Write-Host "[1/3] Compilando API server..." -ForegroundColor Green
Push-Location $API_DIR
pnpm run build
Pop-Location

# Iniciar API server en nueva ventana
Write-Host "[2/3] Iniciando API movil (puerto 5000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$API_DIR'; `$env:NODE_ENV='development'; pnpm run start"

Start-Sleep -Seconds 2

# Iniciar Bot Python en nueva ventana
Write-Host "[3/3] Iniciando Bot Python (puerto 8080)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ROOT'; `$env:DASHBOARD_PORT='8080'; python -u bot.py"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sistema iniciado en ventanas separadas" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
