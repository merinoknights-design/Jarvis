"""
Dónde está instalado Solid Edge en ESTE equipo (2026-11-01).

Cada instalación puede estar en otra carpeta o en otro disco, así que no se fijan rutas. Se lee del registro de Windows
la orden con la que se lanza Solid Edge (SolidEdge.Application → CLSID → LocalServer32 = "...\\Program\\Edge.exe /automation").
JARVIS_SE_RAIZ en .env la fuerza si el registro no sirve (la carpeta que contiene Program, Preferences y Template).
"""
import os
import re
import winreg
from pathlib import Path

import entorno  # noqa: F401  (carga .env)

POR_DEFECTO = Path(r"C:\Program Files\Siemens\Solid Edge 2026")


def edge_del_registro():
    """Ruta de Edge.exe según el registro, o None si Solid Edge no está registrado."""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"SolidEdge.Application\CLSID") as k:
            clsid = winreg.QueryValue(k, None)
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "CLSID\\%s\\LocalServer32" % clsid) as k:
            orden = winreg.QueryValue(k, None)
    except OSError:
        return None
    m = re.match(r'\s*"?(.+?edge\.exe)"?', orden, re.I)
    return Path(m.group(1)) if m else None


def raiz():
    forzada = os.environ.get("JARVIS_SE_RAIZ", "").strip()
    if forzada:
        return Path(forzada)
    edge = edge_del_registro()
    return edge.parent.parent if edge else POR_DEFECTO


def programa():
    """Carpeta con Edge.exe y las type libraries (*.tlb)."""
    return raiz() / "Program"


def tabla_roscas():
    return raiz() / "Preferences" / "HOLES.TXT"


def plantilla_plano():
    return raiz() / "Template" / "ISO Metric" / "iso metric draft.dft"


if __name__ == "__main__":
    for nombre, p in (("raíz", raiz()), ("Program", programa()), ("roscas", tabla_roscas()), ("plantilla", plantilla_plano())):
        print("%-10s %s  %s" % (nombre, "OK " if p.exists() else "FALTA", p))
