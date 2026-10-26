@echo off
chcp 65001 > nul
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   DESCARGANDO MODELO DE IA PARA JARVIS      ║
echo  ║   (Solo necesitas hacer esto UNA vez)        ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Abriendo Ollama...
echo.

REM Iniciar Ollama App primero
start "" "C:\Users\User\AppData\Local\Programs\Ollama\ollama app.exe"
echo  Esperando que Ollama inicie (10 segundos)...
timeout /t 10 /nobreak > nul

echo.
echo  Descargando modelo Qwen 2.5 (7B parametros)
echo  Tamaño: ~4.7 GB - Esto puede tardar varios minutos
echo  segun tu velocidad de internet...
echo.

"C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" pull qwen2.5:7b

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  ============================================
    echo   MODELO DESCARGADO EXITOSAMENTE
    echo   Ya puedes usar iniciar_jarvis.bat
    echo  ============================================
) else (
    echo.
    echo  Hubo un problema. Intenta abriendo Ollama manualmente
    echo  y ejecuta: ollama pull qwen2.5:7b
)
echo.
pause
