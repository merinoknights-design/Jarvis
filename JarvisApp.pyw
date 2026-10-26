import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OLLAMA_APP = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama app.exe"
PYTHON_EXE = BASE_DIR / "venv" / "Scripts" / "python.exe"
SERVER_SCRIPT = BASE_DIR / "server.py"
APP_URL = "http://127.0.0.1:7777"


def is_server_running() -> bool:
    """Verifica si el servidor de Jarvis ya está activo y respondiendo."""
    try:
        req = urllib.request.Request(f"{APP_URL}/api/status", headers={"User-Agent": "JarvisLauncher/2.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama():
    """Inicia Ollama si está instalado y no está corriendo."""
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.8)
    except Exception:
        if OLLAMA_APP.exists():
            try:
                subprocess.Popen(
                    [str(OLLAMA_APP)],
                    creationflags=subprocess.CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0)
                )
            except Exception:
                pass


def ensure_server():
    """Inicia el servidor de Jarvis en segundo plano si no está corriendo."""
    if is_server_running():
        return

    py = str(PYTHON_EXE) if PYTHON_EXE.exists() else sys.executable
    subprocess.Popen(
        [py, str(SERVER_SCRIPT)],
        cwd=str(BASE_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    # Esperar hasta que el servidor responda
    for _ in range(20):
        if is_server_running():
            break
        time.sleep(0.25)


def launch_interface():
    """
    Abre la interfaz táctica de Jarvis en una ventana limpia de aplicación,
    sin flags no admitidos ni advertencias de seguridad del navegador.
    """
    browser_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]

    for browser in browser_candidates:
        if browser.exists():
            try:
                subprocess.Popen([
                    str(browser),
                    f"--app={APP_URL}",
                    "--window-size=1280,820",
                    "--window-position=100,60"
                ])
                return
            except Exception:
                pass

    # Fallback al navegador predeterminado del sistema si no están en rutas estándar
    try:
        os.startfile(APP_URL)
    except Exception:
        pass


if __name__ == "__main__":
    ensure_ollama()
    ensure_server()
    launch_interface()
