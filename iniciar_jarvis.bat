@echo off
chcp 65001 > nul
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     🤖 INICIANDO SISTEMA J.A.R.V.I.S.    ║
echo  ╚══════════════════════════════════════════╝
echo.

echo [1/3] Verificando nucleo Ollama...
start "" "C:\Users\User\AppData\Local\Programs\Ollama\ollama app.exe"
timeout /t 3 /nobreak > nul

echo [2/3] Iniciando Servidor HUD de Jarvis (Puerto 7777)...
start "JARVIS HUD SERVER" cmd /k "C:\Jarvis\venv\Scripts\python.exe C:\Jarvis\server.py"
timeout /t 4 /nobreak > nul

echo [3/3] Abriendo Interfaz Tactica de Jarvis...
start "" http://127.0.0.1:7777

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  ✅ J.A.R.V.I.S. EN LINEA:               ║
echo  ║     http://127.0.0.1:7777                ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
