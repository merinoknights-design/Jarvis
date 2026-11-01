"""
Carga C:\\Jarvis\\.env en os.environ al importarse (Parche JRV-61, 2026-10-30).

Los secretos (p. ej. BRAVE_API_KEY) viven en .env, fuera del código y de git. Cualquier módulo que lea un secreto
al importarse debe hacer `import entorno` antes de leerlo.
"""
import os
from pathlib import Path

ENV = Path(__file__).resolve().parent / ".env"

if ENV.exists():
    for _linea in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in _linea and not _linea.lstrip().startswith("#"):
            _k, _v = _linea.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
