@echo off
chcp 65001 > nul
title Instalador Oficial de J.A.R.V.I.S. (Auto-Actualizable via GitHub)
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║     🤖 INSTALADOR Y SINCRONIZADOR DE J.A.R.V.I.S.        ║
echo  ║     Conectado a Actualizaciones Automaticas por GitHub   ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

REM URL oficial de tu repositorio de GitHub:
set "REPO_URL=https://github.com/merinoknights-design/Jarvis.git"

echo [1/5] Verificando Git y Ollama...
where git >nul 2>&1 || winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
where ollama >nul 2>&1 || winget install --id Ollama.Ollama -e --source winget --accept-package-agreements --accept-source-agreements

echo [2/5] Descargando / Actualizando J.A.R.V.I.S. desde GitHub...
if exist "C:\Jarvis\.git" (
    cd /d C:\Jarvis
    git pull origin main
) else (
    git clone "%REPO_URL%" C:\Jarvis
    cd /d C:\Jarvis
)

echo [3/5] Configurando entorno de Python y dependencias...
if not exist "C:\Jarvis\venv" (
    python -m venv C:\Jarvis\venv
)
C:\Jarvis\venv\Scripts\python.exe -m pip install --upgrade pip
C:\Jarvis\venv\Scripts\pip.exe install -r C:\Jarvis\requirements.txt

echo [4/5] Descargando modelo neuronal rapido (qwen2.5:1.5b)...
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
timeout /t 4 /nobreak > nul
"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" pull qwen2.5:1.5b

echo [5/5] Creando aplicacion y carpeta de J.A.R.V.I.S. en el Escritorio...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut(\"$Desktop\J.A.R.V.I.S..lnk\"); $Shortcut.TargetPath = 'C:\Jarvis\venv\Scripts\pythonw.exe'; $Shortcut.Arguments = 'C:\Jarvis\JarvisApp.pyw'; $Shortcut.WorkingDirectory = 'C:\Jarvis'; $Shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,13'; $Shortcut.Save(); $FolderLink = $WshShell.CreateShortcut(\"$Desktop\Carpeta J.A.R.V.I.S..lnk\"); $FolderLink.TargetPath = 'C:\Jarvis'; $FolderLink.IconLocation = 'C:\Windows\System32\shell32.dll,3'; $FolderLink.Save()"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ✅ J.A.R.V.I.S. INSTALADO Y CONECTADO A GITHUB          ║
echo  ║  Cada vez que lo abras desde el Escritorio se            ║
echo  ║  actualizara automaticamente con la ultima version.      ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
start "" "C:\Jarvis\venv\Scripts\pythonw.exe" "C:\Jarvis\JarvisApp.pyw"
pause
