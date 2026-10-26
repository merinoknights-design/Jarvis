$TargetDir = "C:\Jarvis"
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

Start-Process -FilePath "$TargetDir\venv\Scripts\pythonw.exe" -ArgumentList "$TargetDir\JarvisApp.pyw"
