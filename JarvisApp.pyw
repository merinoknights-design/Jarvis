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
GITHUB_ARCHIVE_URL = "https://github.com/merinoknights-design/Jarvis/archive/refs/heads/main.tar.gz"


def auto_update_from_github() -> bool:
    """Descarga los últimos cambios desde GitHub y devuelve True si actualizó."""
    try:
        tar_file = BASE_DIR / "update_pkg.tar.gz"
        urllib.request.urlretrieve(GITHUB_ARCHIVE_URL, str(tar_file))
        if tar_file.exists():
            subprocess.run(
                ["tar.exe", "-xzf", str(tar_file), "--strip-components=1", "-C", str(BASE_DIR)],
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
            tar_file.unlink(missing_ok=True)
            return True
    except Exception:
        pass
    return False


def is_port_open(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=1.2)
        return True
    except Exception:
        return False


def stop_existing_server():
    """Detiene cualquier instancia vieja de server.py para que tome el código nuevo."""
    try:
        req = urllib.request.Request(f"{APP_URL}/api/shutdown", method="POST")
        urllib.request.urlopen(req, timeout=1.5)
        time.sleep(0.6)
    except Exception:
        pass
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetTCPConnection -LocalPort 7777 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=4
        )
    except Exception:
        pass


def ensure_ollama():
    if not is_port_open("http://127.0.0.1:11434/api/tags"):
        if OLLAMA_APP.exists():
            subprocess.Popen(
                [str(OLLAMA_APP)],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )


def start_fresh_server():
    stop_existing_server()
    py = str(PYTHON_EXE) if PYTHON_EXE.exists() else sys.executable
    subprocess.Popen(
        [py, str(SERVER_SCRIPT)],
        cwd=str(BASE_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    for _ in range(25):
        if is_port_open(f"{APP_URL}/api/status"):
            break
        time.sleep(0.35)


def launch_app_window():
    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]

    for browser in chrome_paths + edge_paths:
        if browser.exists():
            subprocess.Popen([
                str(browser),
                f"--app={APP_URL}",
                "--window-size=1280,800",
                "--window-position=120,80",
                "--title=J.A.R.V.I.S.",
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ])
            return

    os.startfile(APP_URL)


if __name__ == "__main__":
    auto_update_from_github()
    ensure_ollama()
    start_fresh_server()
    launch_app_window()
