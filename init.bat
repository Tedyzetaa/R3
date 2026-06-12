@echo off
echo Iniciando o R2 Tactical OS em modo multithread...

:: 1. Inicia o Llamafile (Servidor do Modelo)
start "R2-Llamafile-Server" llamafile.exe --server --host 127.0.0.1 --port 666 -c 32768 --model oh-dcft-v3.1-claude-3-5-sonnet-20241022.Q3_K_M.gguf

:: Aguarda 5 segundos para o modelo carregar na RAM/VRAM antes de iniciar o Python
timeout /t 5

:: 2. Inicia o Flask (Backend)
start "R2-Main-Flask" cmd /k "call conda activate r2 && python main.py"

:: 3. Inicia o Uplink (Conexão)
start "R2-Uplink-Process" cmd /k "call conda activate r2 && python uplink.py"

echo Processos iniciados com sucesso.
pause