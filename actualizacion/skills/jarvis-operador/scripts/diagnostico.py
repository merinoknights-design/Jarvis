"""
Diagnóstico de Jarvis + Solid Edge (SOLO LECTURA: no lanza, no cierra ni guarda nada).
Uso: C:\\Jarvis\\venv\\Scripts\\python.exe -X utf8 diagnostico.py
"""
import json
import shutil
import sys
import urllib.request
from pathlib import Path

JARVIS = Path(r"C:\Jarvis")
PROYECTOS = Path.home() / "Documents" / "Proyectos_SolidEdge"
URL = "http://127.0.0.1:7777/api/status"


def linea(ok, texto):
    print(("✅ " if ok is True else "⚠️ " if ok is None else "❌ ") + texto)


def main():
    # 1. Disco
    libre_gb = shutil.disk_usage("C:\\").free / 1024 ** 3
    linea(True if libre_gb >= 1.0 else (None if libre_gb >= 0.3 else False),
          "Disco C: %.2f GB libres%s" % (libre_gb, "" if libre_gb >= 1.0 else "  ← avisar al usuario antes de construir"))

    # 2. Servidor de Jarvis
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "diagnostico"}), timeout=3) as r:
            st = json.loads(r.read().decode("utf-8"))
        linea(True, "Jarvis responde en 127.0.0.1:7777 (%s)" % st.get("active_model", "?"))
    except Exception as e:
        linea(False, "Jarvis NO responde en 127.0.0.1:7777 (%s). Arranque: C:\\Jarvis\\iniciar_jarvis.bat" % type(e).__name__)

    # 3. Código clave presente
    for rel in ["server.py", "se_com_seguro.py", r"cardan\ensamblar_cardan.py", r"cardan\prueba_giro.py", r"venv\Scripts\python.exe",
                r"agente\csharp\InterferenciaTipada.exe"]:
        p = JARVIS / rel
        linea(p.exists(), "%s %s" % (rel, "presente" if p.exists() else "FALTA"))
    if not (JARVIS / "agente" / "csharp" / "InterferenciaTipada.exe").exists():
        print("     → sin él no hay detección de choques: python -X utf8 C:\\Jarvis\\agente\\csharp\\compilar.py")
    try:
        sys.path.insert(0, str(JARVIS))
        import rutas_se
        linea((rutas_se.programa() / "Edge.exe").exists(), "Instalación de Solid Edge: %s" % rutas_se.raiz())
    except Exception as e:
        linea(None, "No pude detectar la instalación de Solid Edge (%s)" % e)

    # 4. Solid Edge (solo si ya está abierto)
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        app = win32com.client.GetActiveObject("SolidEdge.Application")
        linea(True, "Solid Edge abierto · versión %s · %d documento(s)" % (app.Version, app.Documents.Count))
        for i in range(1, app.Documents.Count + 1):
            d = app.Documents.Item(i)
            try:
                extra = "sin guardar" if d.Dirty else "guardado"
            except Exception:
                extra = "?"
            print("     - %s  [%s]  %s" % (d.Name, extra, getattr(d, "FullName", "")))
    except Exception:
        linea(None, "Solid Edge no está abierto (se abrirá solo al primer uso por COM, tarda ~20 s)")

    # 5. Estado del Cardán
    try:  # JRV-69: la ruta del Cardán vive en C:\Jarvis\cardan\rutas_cardan.py
        sys.path.insert(0, str(JARVIS))
        from cardan.rutas_cardan import ASM as CARDAN_ASM
        est = CARDAN_ASM.with_name("cardan_estado.json")
    except Exception:
        est = PROYECTOS / "Cardan" / "cardan_estado.json"
    if est.exists():
        e = json.loads(est.read_text(encoding="utf-8"))
        fases = e.get("fases", [])
        linea(True if fases == [1, 2, 3, 4, 5] else None, "Cardán: fases hechas %s · %s" % (fases, est.parent / "Cardan.asm"))
    else:
        linea(None, "Cardán: sin corrida oficial en %s" % est.parent)

    # 5b. Subidas recientes a Jarvis: un PDF o imagen subido puede haber quedado como plano PENDIENTE
    #     y un "sí"/"sigue" posterior lo mandaría a modelar con plantillas.
    import time
    subidas = JARVIS / "uploads"
    if subidas.exists():
        recientes = [p for p in subidas.iterdir() if p.is_file() and time.time() - p.stat().st_mtime < 86400]
        if recientes:
            linea(None, "Subidas a Jarvis en las últimas 24 h (posibles planos pendientes): " +
                  ", ".join(p.name for p in recientes[:8]))

    # 6. Otros proyectos con estado de fases
    if PROYECTOS.exists():
        otros = [p for p in PROYECTOS.glob("*/*_estado.json") if p.parent.name != "Cardan"]
        for p in otros:
            try:
                linea(None, "Proyecto %s: fases %s" % (p.parent.name, json.loads(p.read_text(encoding="utf-8")).get("fases")))
            except Exception:
                pass

    print("\nAntes de operar: lee memoria/lecciones.md de la habilidad jarvis-operador.")


if __name__ == "__main__":
    sys.exit(main())
