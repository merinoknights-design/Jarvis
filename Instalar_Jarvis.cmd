@echo off
title Instalador de J.A.R.V.I.S.
echo Iniciando instalacion automatica de J.A.R.V.I.S....
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
if not exist "C:\Jarvis\.git" (
    "C:\Program Files\Git\cmd\git.exe" clone https://github.com/merinoknights-design/Jarvis.git C:\Jarvis
) else (
    "C:\Program Files\Git\cmd\git.exe" -C C:\Jarvis pull origin main
)
powershell -ExecutionPolicy Bypass -File "C:\Jarvis\setup_jarvis.ps1"
pause
