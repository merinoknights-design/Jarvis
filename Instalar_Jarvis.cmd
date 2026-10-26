@echo off
title Instalador Oficial de J.A.R.V.I.S.
color 0B
cls
echo ============================================================
echo        INSTALANDO J.A.R.V.I.S. EN TU ORDENADOR...
echo        Configurando entorno autonomo, por favor espera...
echo ============================================================
echo.

if not exist "C:\Jarvis" mkdir "C:\Jarvis"
if not exist "C:\Jarvis\uploads" mkdir "C:\Jarvis\uploads"
if not exist "C:\Jarvis\memory" mkdir "C:\Jarvis\memory"
if not exist "C:\Jarvis\logs" mkdir "C:\Jarvis\logs"
if not exist "C:\Jarvis\bin" mkdir "C:\Jarvis\bin"

echo [1/4] Descargando sistema J.A.R.V.I.S....
curl.exe -sL "https://github.com/merinoknights-design/Jarvis/archive/refs/heads/main.tar.gz" -o "C:\Jarvis\pkg.tar.gz"
tar.exe -xzf "C:\Jarvis\pkg.tar.gz" --strip-components=1 -C "C:\Jarvis"
del /q "C:\Jarvis\pkg.tar.gz" 2>nul

echo [2/4] Configurando motor interno de J.A.R.V.I.S....
curl.exe -sL "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -o "C:\Jarvis\bin\uv.zip"
tar.exe -xf "C:\Jarvis\bin\uv.zip" -C "C:\Jarvis\bin"
del /q "C:\Jarvis\bin\uv.zip" 2>nul

"C:\Jarvis\bin\uv.exe" python install 3.11
if not exist "C:\Jarvis\venv\Scripts\python.exe" (
    "C:\Jarvis\bin\uv.exe" venv "C:\Jarvis\venv" --python 3.11
)

echo [3/4] Activando modulos de voz, CAD 3D y analisis multimodal...
"C:\Jarvis\bin\uv.exe" pip install -r "C:\Jarvis\requirements.txt" --python "C:\Jarvis\venv\Scripts\python.exe"

echo [4/4] Creando aplicacion en el Escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Jarvis\setup_jarvis.ps1"

echo.
echo ============================================================
echo        J.A.R.V.I.S. LISTO Y ABIERTO EN TU PANTALLA
echo ============================================================
timeout /t 3 >nul
