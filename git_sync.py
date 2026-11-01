import datetime
import hashlib
import shutil
import subprocess
import urllib.request
from pathlib import Path

BASE_DIR = Path("C:/Jarvis")
GIT_EXE = r"C:\Program Files\Git\cmd\git.exe"
GITHUB_TAR = "https://github.com/merinoknights-design/Jarvis/archive/refs/heads/main.tar.gz"
RESPALDOS = Path("C:/Jarvis_respaldos")
EXT_CODIGO = {".py", ".pyw", ".html", ".js", ".css", ".json", ".bat", ".txt", ".md"}
IGNORAR = {"venv", "__pycache__", "uploads", ".git", "node_modules"}


def run_git(args: list) -> str:
    cmd = [GIT_EXE if Path(GIT_EXE).exists() else "git"] + args
    res = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return (res.stdout + "\n" + res.stderr).strip()


def ensure_repo_initialized() -> str:
    if not (BASE_DIR / ".git").exists():
        run_git(["init", "-b", "main"])
        run_git(["config", "user.name", "Jarvis Core"])
        run_git(["config", "user.email", "jarvis@local.ai"])
    return "Repositorio Git local activo."


def set_github_remote(repo_url: str) -> str:
    ensure_repo_initialized()
    remotes = run_git(["remote"])
    if "origin" in remotes:
        run_git(["remote", "set-url", "origin", repo_url])
    else:
        run_git(["remote", "add", "origin", repo_url])
    return f"Repositorio remoto de GitHub vinculado exitosamente a: {repo_url}"


def push_update_to_github(commit_msg: str = "") -> str:
    ensure_repo_initialized()
    if not commit_msg:
        commit_msg = f"Actualización automática de J.A.R.V.I.S. ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
    run_git(["add", "."])
    commit_out = run_git(["commit", "-m", commit_msg])
    push_out = run_git(["push", "-u", "origin", "main"])
    if "origin" not in run_git(["remote"]):
        return (
            f"Cambios guardados en el repositorio Git local (`{commit_msg}`).\n"
            f"Para publicarlos en la nube, dígame: 'Conecta el repositorio https://github.com/TU_USUARIO/Jarvis.git'"
        )
    return f"🚀 ¡Actualización subida a GitHub, Señor! Todos los ordenadores conectados recibirán esta versión automáticamente.\nDetalle:\n{push_out or commit_out}"


def _huellas_codigo(raiz: Path) -> dict:
    out = {}
    for p in raiz.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXT_CODIGO and not (IGNORAR & set(p.relative_to(raiz).parts)):
            out[str(p.relative_to(raiz)).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def revisar_actualizacion_github() -> str:
    """Parche JRV-60 (2026-10-28): antes "actualízate" descomprimía el paquete de GitHub ENCIMA de C:\\Jarvis
    y borraba sin aviso los parches locales (capa COM segura, receta del Cardán, JRV-11…). Ahora lo descarga
    aparte, lo compara con lo instalado y NO sobrescribe nada: aplicar cambios es una decisión aparte."""
    libre_gb = shutil.disk_usage("C:\\").free / 1024 ** 3
    if libre_gb < 0.3:
        return f"No descargo la actualización, Señor: quedan {libre_gb:.2f} GB libres en C:."
    destino = RESPALDOS / (datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_github")
    destino.mkdir(parents=True, exist_ok=True)
    tar = destino / "paquete.tar.gz"
    try:
        urllib.request.urlretrieve(GITHUB_TAR, str(tar))
        subprocess.run(["tar.exe", "-xzf", str(tar), "--strip-components=1", "-C", str(destino)],
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=120, check=True)
    except Exception as e:
        return f"No pude descargar la versión de GitHub: {e}"
    finally:
        tar.unlink(missing_ok=True)
    remota, local = _huellas_codigo(destino), _huellas_codigo(BASE_DIR)
    cambian = sorted(f for f in remota if f in local and remota[f] != local[f])
    nuevos = sorted(f for f in remota if f not in local)
    solo_local = sorted(f for f in local if f not in remota)

    def lista(xs):
        return "\n".join(f"  • {x}" for x in xs[:25]) + (f"\n  … y {len(xs) - 25} más" if len(xs) > 25 else "") if xs else "  (ninguno)"

    return (f"Descargué la versión de GitHub en {destino} y NO toqué nada de C:\\Jarvis, Señor.\n"
            f"Archivos que GitHub cambiaría ({len(cambian)}):\n{lista(cambian)}\n"
            f"Archivos nuevos en GitHub ({len(nuevos)}):\n{lista(nuevos)}\n"
            f"Archivos que solo existen aquí y se conservan ({len(solo_local)}):\n{lista(solo_local)}\n"
            "Si los cambios valen la pena, se aplican uno a uno revisando que no borren los parches locales.")


def pull_update_from_github() -> str:
    ensure_repo_initialized()
    if "origin" not in run_git(["remote"]):
        return "El repositorio Git local está al día, pero aún no se ha vinculado una URL remota de GitHub."
    out = run_git(["pull", "--rebase", "--autostash", "origin", "main"])
    return f"🔄 Sincronización desde GitHub completada, Señor:\n{out}"
