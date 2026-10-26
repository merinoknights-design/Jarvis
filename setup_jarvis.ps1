# Instalador Oficial de J.A.R.V.I.S. para Windows
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       INSTALADOR OFICIAL DE J.A.R.V.I.S. (v2.0)            " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$TargetDir = "C:\Jarvis"
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\memory" | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\logs" | Out-Null

Write-Host "[1/5] Verificando Git y Ollama a traves de Microsoft Winget..." -ForegroundColor Yellow
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
winget install --id Ollama.Ollama -e --source winget --accept-package-agreements --accept-source-agreements

$GitExe = "C:\Program Files\Git\cmd\git.exe"
if (-not (Test-Path $GitExe)) {
    $GitExe = "git"
}

Write-Host "[2/5] Sincronizando codigo fuente desde GitHub (merinoknights-design/Jarvis)..." -ForegroundColor Yellow
if (Test-Path "$TargetDir\.git") {
    & $GitExe -C $TargetDir pull origin main
} else {
    & $GitExe clone "https://github.com/merinoknights-design/Jarvis.git" "$TargetDir\repo_tmp"
    if (Test-Path "$TargetDir\repo_tmp") {
        Copy-Item -Path "$TargetDir\repo_tmp\*" -Destination $TargetDir -Recurse -Force
        Remove-Item -Path "$TargetDir\repo_tmp" -Recurse -Force
    }
}

Write-Host "[3/5] Configurando entorno Python 3.11 para J.A.R.V.I.S...." -ForegroundColor Yellow
pip install uv
$UvxDir = "$env:APPDATA\Python\Python314\Scripts"
$UvExe = "uv"
if (Test-Path "$UvxDir\uv.exe") {
    $UvExe = "$UvxDir\uv.exe"
}
& $UvExe python install 3.11
if (-not (Test-Path "$TargetDir\venv\Scripts\python.exe")) {
    & $UvExe venv "$TargetDir\venv" --python 3.11
}
& $UvExe pip install -r "$TargetDir\requirements.txt" --python "$TargetDir\venv\Scripts\python.exe"

Write-Host "[4/5] Descargando modelo neuronal rapido (qwen2.5:1.5b)..." -ForegroundColor Yellow
$OllamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (Test-Path $OllamaExe) {
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    & $OllamaExe pull qwen2.5:1.5b
}

Write-Host "[5/5] Creando icono J.A.R.V.I.S. y Carpeta en el Escritorio..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")

$AppLink = $WshShell.CreateShortcut("$Desktop\J.A.R.V.I.S..lnk")
$AppLink.TargetPath = "$TargetDir\venv\Scripts\pythonw.exe"
$AppLink.Arguments = "$TargetDir\JarvisApp.pyw"
$AppLink.WorkingDirectory = $TargetDir
$AppLink.IconLocation = "C:\Windows\System32\shell32.dll,13"
$AppLink.Save()

$DirLink = $WshShell.CreateShortcut("$Desktop\Carpeta J.A.R.V.I.S..lnk")
$DirLink.TargetPath = $TargetDir
$DirLink.IconLocation = "C:\Windows\System32\shell32.dll,3"
$DirLink.Save()

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  J.A.R.V.I.S. INSTALADO EXITOSAMENTE EN TU ESCRITORIO      " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Start-Process -FilePath "$TargetDir\venv\Scripts\pythonw.exe" -ArgumentList "$TargetDir\JarvisApp.pyw"
