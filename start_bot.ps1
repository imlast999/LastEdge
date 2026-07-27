# Script ejecutor de bot.py para PowerShell sin bloqueos de Ctrl+C
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   BOT MT5 - Trading Automatizado (PS) " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

try {
    python -u bot.py
} finally {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "BOT DETENIDO CLEANMENTE" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}
