# ===========================================
# Script para rodar API com Mocks Azure (PowerShell)
# ===========================================

Write-Host "🚀 Iniciando ambiente com mocks Azure..." -ForegroundColor Green
Write-Host ""
Write-Host "   API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   Mock Text: http://localhost:3001" -ForegroundColor Cyan
Write-Host "   Mock Speech: http://localhost:3002" -ForegroundColor Cyan
Write-Host "   Mock Vision: http://localhost:3003" -ForegroundColor Cyan
Write-Host ""

# Subir serviços
docker-compose -f docker-compose.mock.yml up --build @args
