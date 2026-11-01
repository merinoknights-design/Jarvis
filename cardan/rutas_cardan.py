"""
Rutas del Cardán: el ÚNICO sitio donde se definen (JRV-69, 2026-10-28).

La carpeta de cada usuario va en JARVIS_CARDAN_RAIZ, en .env (fuera de git); sin ella, Documents\\Proyectos_SolidEdge.
Si el proyecto se mueve:
  1. muévelo con el Gestor de diseños / Empaquetar proyecto de Solid Edge (o redirige los vínculos del .asm
     con Revision Manager, como se hizo el 2026-10-28), y
  2. cambia JARVIS_CARDAN_RAIZ. server.py, ensamblar_cardan.py, inspeccionar_piezas.py y agente/acciones.py leen de aquí.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import entorno  # noqa: E402,F401  (carga .env)

RAIZ = Path(os.environ.get("JARVIS_CARDAN_RAIZ") or Path.home() / "Documents" / "Proyectos_SolidEdge")
CARPETA_PIEZAS = RAIZ / "CAD Cardan"
ASM = RAIZ / "Cardan" / "Cardan.asm"
