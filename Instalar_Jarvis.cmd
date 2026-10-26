@echo off
title Instalador y Actualizador Oficial de J.A.R.V.I.S.
color 0B
cls
echo ============================================================
echo        INSTALANDO / ACTUALIZANDO J.A.R.V.I.S....
echo ============================================================
echo.

REM Cerrar cualquier servidor viejo de Jarvis en memoria para aplicar la actualizacion
taskkill /F /IM pythonw.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

if not exist "C:\Jarvis" mkdir "C:\Jarvis"
if not exist "C:\Jarvis\uploads" mkdir "C:\Jarvis\uploads"
if not exist "C:\Jarvis\memory" mkdir "C:\Jarvis\memory"
if not exist "C:\Jarvis\logs" mkdir "C:\Jarvis\logs"
if not exist "C:\Jarvis\bin" mkdir "C:\Jarvis\bin"

echo [1/4] Descargando ultima version de J.A.R.V.I.S. desde GitHub...
curl.exe -sL "https://github.com/merinoknights-design/Jarvis/archive/refs/heads/main.tar.gz" -o "C:\Jarvis\pkg.tar.gz"
tar.exe -xzf "C:\Jarvis\pkg.tar.gz" --strip-components=1 -C "C:\Jarvis"
del /q "C:\Jarvis\pkg.tar.gz" 2>nul

echo [2/4] Verificando motor interno de J.A.R.V.I.S....
if not exist "C:\Jarvis\bin\uv.exe" (
    curl.exe -sL "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -o "C:\Jarvis\bin\uv.zip"
    tar.exe -xf "C:\Jarvis\bin\uv.zip" -C "C:\Jarvis\bin"
    del /q "C:\Jarvis\bin\uv.zip" 2>nul
)

"C:\Jarvis\bin\uv.exe" python install 3.11
if not exist "C:\Jarvis\venv\Scripts\python.exe" (
    "C:\Jarvis\bin\uv.exe" venv "C:\Jarvis\venv" --python 3.11
)

echo [3/4] Verificando modulos de voz, busqueda y CAD...
"C:\Jarvis\bin\uv.exe" pip install -r "C:\Jarvis\requirements.txt" --python "C:\Jarvis\venv\Scripts\python.exe"

echo [4/4] Iniciando J.A.R.V.I.S. actualizado...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Jarvis\setup_jarvis.ps1"

echo.
echo ============================================================
echo        J.A.R.V.I.S. ACTUALIZADO Y EN LINEA
echo ============================================================
timeout /t 2 >nul
