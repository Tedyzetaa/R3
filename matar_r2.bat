@echo off
echo Encerrando R2 Tactical OS...
taskkill /f /im llamafile.exe >nul 2>&1
echo [OK] Llamafile encerrado.
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo [OK] Servidor Flask encerrado.
echo R2 Tactical OS desligado com sucesso.
pause