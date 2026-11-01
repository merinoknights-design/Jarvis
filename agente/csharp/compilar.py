"""
Compila en ESTE equipo las ayudas en C# que Python no puede reemplazar (JRV-24). 2026-11-01. No instala nada.

Usa el compilador que trae Windows (.NET Framework) y las type libraries del Solid Edge instalado:
  1. GenerarInterop.exe → interop\\Interop.*.dll (interop tipado, propio de cada instalación).
  2. InterferenciaTipada.exe, que ejecuta el comando de interferencia.
Por eso estos binarios no van en el repositorio: se generan aquí. Se puede repetir sin riesgo.

Uso:  python -X utf8 compilar.py
Última línea:  @@RESULTADO@@ {json}
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent))
import rutas_se  # noqa: E402

MARCA = "@@RESULTADO@@"
CSC = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
TLBS = ["assembly.tlb", "constant.tlb"]
REFERENCIAS = ["SolidEdgeFramework", "SolidEdgeAssembly", "SolidEdgeConstants"]


def correr(args):
    r = subprocess.run([str(a) for a in args], cwd=str(AQUI), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError("Falló %s: %s" % (Path(args[0]).name, (r.stdout + r.stderr)[-800:]))


def main():
    if not CSC.exists():
        raise RuntimeError("No encuentro el compilador de .NET Framework en %s" % CSC)
    prog = rutas_se.programa()
    tlbs = [prog / t for t in TLBS]
    faltan = [str(t) for t in tlbs if not t.exists()]
    if faltan:
        raise RuntimeError("No encuentro las type libraries de Solid Edge: %s. ¿Está instalado? Si está en otra carpeta, "
                           "pon JARVIS_SE_RAIZ en .env." % faltan)
    correr([CSC, "/nologo", "/out:GenerarInterop.exe", "GenerarInterop.cs"])
    correr([AQUI / "GenerarInterop.exe", AQUI / "interop"] + tlbs)
    dlls = sorted((AQUI / "interop").glob("Interop.*.dll"))
    for d in dlls:      # InterferenciaTipada.exe las necesita a su lado al ejecutarse
        shutil.copy2(d, AQUI / d.name)
    refs = ["/r:interop\\Interop.%s.dll" % n for n in REFERENCIAS]
    correr([CSC, "/nologo"] + refs + ["/out:InterferenciaTipada.exe", "InterferenciaTipada.cs"])
    return {"ok": (AQUI / "InterferenciaTipada.exe").exists(), "solid_edge": str(prog), "interop": [d.name for d in dlls],
            "programa": str(AQUI / "InterferenciaTipada.exe")}


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": str(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get("ok") else 1)
