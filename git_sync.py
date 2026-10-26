import datetime
import subprocess
from pathlib import Path

BASE_DIR = Path("C:/Jarvis")
GIT_EXE = r"C:\Program Files\Git\cmd\git.exe"


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


def pull_update_from_github() -> str:
    ensure_repo_initialized()
    if "origin" not in run_git(["remote"]):
        return "El repositorio Git local está al día, pero aún no se ha vinculado una URL remota de GitHub."
    out = run_git(["pull", "--rebase", "--autostash", "origin", "main"])
    return f"🔄 Sincronización desde GitHub completada, Señor:\n{out}"
