$uvxPath = "C:\Users\User\AppData\Roaming\Python\Python314\Scripts"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*Python314\Scripts*") {
    $newPath = $currentPath + ";" + $uvxPath
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "✅ PATH actualizado - uvx ya disponible en terminales nuevas"
} else {
    Write-Host "✅ uvx ya estaba en PATH"
}
